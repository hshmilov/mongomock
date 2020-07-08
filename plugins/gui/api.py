import logging
import math
import json
from datetime import datetime
from itertools import islice
from typing import List

from flask import g, has_request_context, jsonify, request
from passlib.hash import bcrypt

from axonius.consts.adapter_consts import CONNECTION_LABEL
from axonius.consts.gui_consts import IS_AXONIUS_ROLE, RootMasterNames
from axonius.consts.metric_consts import ApiMetric
from axonius.consts.plugin_consts import (DEVICE_CONTROL_PLUGIN_NAME, NODE_ID,
                                          PLUGIN_NAME)
from axonius.consts.scheduler_consts import SCHEDULER_CONFIG_NAME
from axonius.logging.metric_helper import log_metric
from axonius.plugin_base import EntityType, PluginBase, return_error
from axonius.utils.db_querying_helper import get_entities
from axonius.utils.gui_helpers import accounts as accounts_filter
from axonius.utils.gui_helpers import (add_rule_custom_authentication,
                                       add_rule_unauth, entity_fields,
                                       filtered, filtered_entities,
                                       get_entities_count, historical,
                                       log_activity_rule, paginated, projected)
from axonius.utils.gui_helpers import schema_fields as schema
from axonius.utils.gui_helpers import sorted_endpoint
from axonius.utils.metric import remove_ids
from axonius.utils.permissions_helper import (PermissionAction,
                                              PermissionCategory,
                                              PermissionValue,
                                              deserialize_db_permissions,
                                              is_axonius_role)
from axonius.utils.root_master.root_master import restore_from_s3_key
from gui.logic.entity_data import entity_tasks, get_entity_data
from gui.logic.historical_dates import all_historical_dates
from gui.logic.routing_helper import check_permissions

logger = logging.getLogger(f'axonius.{__name__}')

API_VERSION = '1'
API_CLIENT_VERSION = '3.1.4'
DEVICE_ASSETS_VIEW = PermissionValue.get(PermissionAction.View, PermissionCategory.DevicesAssets)
DEVICE_ASSETS_UPDATE = PermissionValue.get(PermissionAction.Update, PermissionCategory.DevicesAssets)
USER_ASSETS_VIEW = PermissionValue.get(PermissionAction.View, PermissionCategory.UsersAssets)
USER_ASSETS_UPDATE = PermissionValue.get(PermissionAction.Update, PermissionCategory.UsersAssets)


# pylint: disable=protected-access,no-self-use,no-member,too-many-lines

# Caution! These decorators must come BEFORE @add_rule


def basic_authentication(func, required_permission: PermissionValue, enforce_permissions: bool = True):
    """
    Decorator stating that the view requires the user to be connected
    """

    def wrapper(self, *args, **kwargs):
        users_collection = self._get_collection('users')
        roles_collection = self._get_collection('roles')

        def check_auth_user(username, password):
            """
            This function is called to check if a username /
            password combination is valid.
            """

            user_from_db = users_collection.find_one({'user_name': username})

            if user_from_db is None:
                logger.info(f'Unknown user {username} tried logging in')
                return None, None

            role = roles_collection.find_one({'_id': user_from_db.get('role_id')})

            if not bcrypt.verify(password, user_from_db['password']):
                return None, None

            is_expired = (PluginBase.Instance.trial_expired() or PluginBase.Instance.contract_expired())

            if is_expired and not role.get(IS_AXONIUS_ROLE):
                return None, None

            role_permissions = deserialize_db_permissions(role['permissions'])

            if user_from_db.get('name') == 'admin':
                return user_from_db, role_permissions

            if enforce_permissions and not check_permissions(role_permissions, required_permission):
                return None, None

            return user_from_db, role_permissions

        def check_auth_api_key(api_key, api_secret):
            """
            This function is called to check if an api key and secret match
            """
            user_from_db = users_collection.find_one({
                'api_key': api_key,
                'api_secret': api_secret
            })

            if not user_from_db:
                return None, None

            role = roles_collection.find_one({'_id': user_from_db.get('role_id')})

            is_expired = (PluginBase.Instance.trial_expired() or PluginBase.Instance.contract_expired())

            if is_expired and not is_axonius_role(role):
                return None, None

            role = roles_collection.find_one({'_id': user_from_db.get('role_id')})
            role_permissions = deserialize_db_permissions(role['permissions'])

            if user_from_db.get('admin'):
                return user_from_db, role_permissions

            if enforce_permissions and not check_permissions(role_permissions, required_permission):
                return None, None

            return user_from_db, role_permissions

        api_auth = request.headers.get('api-key'), request.headers.get('api-secret')
        auth = request.authorization
        user_from_db, permissions = check_auth_api_key(*api_auth)

        if not user_from_db and auth:
            user_from_db, permissions = check_auth_user(auth.username, auth.password)

        if user_from_db:

            if has_request_context():
                path = request.path
                cleanpath = remove_ids(path)
                log_metric(logger, ApiMetric.PUBLIC_REQUEST_PATH, cleanpath, method=request.method)

            # save the associated user for the local request
            g.api_request_user = user_from_db
            g.api_user_permissions = permissions
            return func(self, *args, **kwargs)

        return return_error('Unauthorized', 401)

    return wrapper


def api_add_rule(rule,
                 *args,
                 required_permission: PermissionValue,
                 activity_params: List[str] = None,
                 skip_activity: bool = False,
                 enforce_permissions: bool = True,
                 **kwargs,
                 ):
    """
    A URL mapping for API endpoints that use the API method to log in (either user and pass or API key)
    """
    def wrapper(func):
        def basic_authentication_permissions(*args, **kwargs):
            return basic_authentication(
                *args,
                **kwargs,
                required_permission=required_permission,
                enforce_permissions=enforce_permissions,
            )

        authenticated_rule = add_rule_custom_authentication(
            rule=f'V{API_VERSION}/{rule}',
            auth_method=basic_authentication_permissions,
            *args,
            **kwargs,
        )
        if skip_activity:
            return authenticated_rule(func)

        activity_category = required_permission.Category.value
        if required_permission.Section:
            activity_category = f'{activity_category}.{required_permission.Section.value}'

        return log_activity_rule(
            rule=rule,
            activity_category=activity_category,
            activity_param_names=activity_params,
        )(authenticated_rule(func))

    return wrapper


def get_page_metadata(skip, limit, number_of_assets):
    logger.info(f'skip this:{skip}')
    logger.info(f'limit this:{limit}')
    return {
        'number': math.floor((skip / limit) + 1) if limit != 0 else 0,  # Current page number
        'size': min(max(number_of_assets - skip, 0), limit),  # Number of assets in current page
        'totalPages': math.ceil(number_of_assets / limit) if limit != 0 else 0,  # Total number of pages
        'totalResources': number_of_assets  # Total number of assets filtered
    }


class APIMixin:

    ##########
    # UNAUTH #
    ##########

    @add_rule_unauth(
        rule='api',
        methods=['GET'],
    )
    def api_description(self):
        return API_VERSION

    @add_rule_unauth(
        rule='signup_api',
        methods=['POST', 'GET']
    )
    def api_public_signup(self):
        """Process initial signup.

        jim: 3.3: added for esentire/cimpress automation

        :return: dict
        """
        return self._process_signup(return_api_keys=True)

    ##########
    # SYSTEM #
    ##########

    @api_add_rule(
        rule='system/central_core',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Settings)
    )
    def central_core_get(self):
        """Get the current central core (root master) settings from feature flags.

        jim: 3.3: added for esentire/cimpress automation

        :return: dict
        """
        return self._get_central_core_settings()

    @api_add_rule(
        rule='system/central_core',
        methods=['POST'],
        required_permission=PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings)
    )
    def central_core_update(self):
        """Update the current central core (root master) settings from feature flags.

        jim: 3.3: added for esentire/cimpress automation

        :return: dict
        """
        return self._update_central_core_settings()

    @api_add_rule(
        rule='system/central_core/restore',
        methods=['POST'],
        required_permission=PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings)
    )
    def central_core_restore(self):
        """Start the restore process.

        jim: 3.3: added for esentire/cimpress automation

        restore_type: str, required
            type of restore to perform

        :return: dict
        """
        request_data = self.get_request_data_as_object()
        restore_type = request_data.get('restore_type')
        restore_types = {'aws': self.central_core_restore_aws}

        if restore_type not in restore_types:
            restore_types = ', '.join(list(restore_types))
            err = f'Invalid restore_type={restore_type!r}, must be one of: {restore_types}'
            return return_error(error_message=err, http_status=400, additional_data=None)

        restore_method = restore_types[restore_type]
        return restore_method(request_data=request_data)

    def central_core_restore_aws(self, request_data):
        """Perform a restore from an AWS S3.

        jim: 3.3: added for esentire/cimpress automation

        :return: dict
        """
        explain = {
            'key_name': {
                'type': 'str',
                'required': True,
                'description': 'Name of file in [bucket_name] to restore',
                'default': None,
            },
            'bucket_name': {
                'type': 'str',
                'required': False,
                'description': 'Name of bucket in S3 to get [key_name] from',
                'default': 'Global Settings > Amazon S3 Settings > Amazon S3 bucket name',
            },
            'access_key_id': {
                'type': 'str',
                'required': False,
                'description': 'AWS Access Key Id to use to access [bucket_name]',
                'default': 'Global Settings > Amazon S3 Settings > AWS Access Key Id',
            },
            'secret_access_key': {
                'type': 'str',
                'required': False,
                'description': 'AWS Secret Access Key to use to access [bucket_name]',
                'default': 'Global Settings > Amazon S3 Settings > AWS Secret Access Key',
            },
            'preshared_key': {
                'type': 'str',
                'required': False,
                'description': 'Password to use to decrypt [key_name]',
                'default': 'Global Settings > Amazon S3 Settings > Backup encryption passphrase',
            },
            'allow_re_restore': {
                'type': 'bool',
                'required': False,
                'description': 'Restore [key_name] even if it has already been restored',
                'default': False,
            },
            'delete_backups': {
                'type': 'bool',
                'required': False,
                'description': 'Delete [key_name] from [bucket_name] after restore has finished',
                'default': False,
            },
        }

        root_master_settings = self.feature_flags_config().get(RootMasterNames.root_key) or {}
        aws_s3_settings = self._aws_s3_settings.copy()

        restore_opts = {}
        restore_opts['key_name'] = request_data.get('key_name')
        restore_opts['bucket_name'] = aws_s3_settings.get('bucket_name', None)
        restore_opts['preshared_key'] = aws_s3_settings.get('preshared_key', None)
        restore_opts['access_key_id'] = aws_s3_settings.get('aws_access_key_id', None)
        restore_opts['secret_access_key'] = aws_s3_settings.get('aws_secret_access_key', None)
        restore_opts['delete_backups'] = root_master_settings.get('delete_backups', False)
        restore_opts['allow_re_restore'] = request_data.get('allow_re_restore', False)

        if request_data.get('delete_backups', None) is not None:
            restore_opts['delete_backups'] = request_data['delete_backups']

        s3_keys = ['access_key_id', 'secret_access_key', 'bucket_name', 'preshared_key', 'access_key_id']
        for s3_key in s3_keys:
            if request_data.get(s3_key, None) is not None:
                restore_opts[s3_key] = request_data[s3_key]

        key_name = restore_opts['key_name']
        bucket_name = restore_opts['bucket_name']

        if not key_name:
            err = f'Must supply \'key_name\' of object in bucket {bucket_name!r}'
            return return_error(error_message=err, http_status=400, additional_data=explain)

        try:
            obj_meta = restore_from_s3_key(**restore_opts)

            try:
                obj_bytes = obj_meta['ContentLength']
                obj_gb = round(obj_bytes / (1024 ** 3), 3)
            except Exception:
                obj_gb = '???'

            return_data = {
                'status': 'success',
                'message': f'Successfully restored backup file',
                'additional_data': {
                    'bucket_name': bucket_name,
                    'key_name': key_name,
                    'key_size_gb': obj_gb,
                    'key_modified_dt': obj_meta.get('LastModified', None),
                    'key_deleted': obj_meta.get('deleted', None),
                    'key_re_restored': obj_meta.get('re_restored', None),
                },
            }

            return jsonify(return_data)
        except Exception as exc:
            err = f'Failure while restoring: {exc}'
            return return_error(error_message=err, http_status=400, additional_data=explain)

    def _api_get_settings_json(self, plugin_name, config_name):
        """Get a plugins settings and schemas in JSON format.

        :return: str
        """
        config_obj, config_schema = self._get_plugin_configs(plugin_unique_name=plugin_name, config_name=config_name)
        return jsonify({'config': config_obj, 'schema': config_schema})

    def _api_update_settings(self, plugin_name, config_name):
        """Update a plugins settings and return the updated settings in JSON format.

        :return: str
        """
        self._save_plugin_config(plugin_unique_name=plugin_name, config_name=config_name)
        return self._api_get_settings_json(plugin_name=plugin_name, config_name=config_name)

    @api_add_rule(
        rule='system/settings/lifecycle',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Settings),
    )
    def get_api_settings_lifecycle(self):
        """Get System Settings > Lifecycle settings tab.

        :return: dict
        """
        plugin_name = 'system_scheduler'
        return self._api_get_settings_json(plugin_name=plugin_name, config_name=SCHEDULER_CONFIG_NAME)

    @api_add_rule(
        rule='system/settings/lifecycle',
        methods=['POST'],
        required_permission=PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings),
    )
    def update_api_settings_lifecycle(self):
        """Update System Settings > Lifecycle settings tab.

        :return: dict
        """
        plugin_name = 'system_scheduler'
        return self._api_update_settings(plugin_name=plugin_name, config_name=SCHEDULER_CONFIG_NAME)

    @api_add_rule(
        rule='system/settings/gui',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Settings),
    )
    def get_api_settings_gui(self):
        """Get System Settings > GUI settings tab.

        :return: dict
        """
        plugin_name = 'gui'
        config_name = 'GuiService'
        return self._api_get_settings_json(plugin_name=plugin_name, config_name=config_name)

    @api_add_rule(
        rule='system/settings/gui',
        methods=['POST'],
        required_permission=PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings),
    )
    def update_api_settings_gui(self):
        """Get or set System Settings > GUI settings tab.

        POST: Returns empty str. POST body is dict returned by GET with updated values.

        :return: dict or str
        """
        plugin_name = 'gui'
        config_name = 'GuiService'
        return self._api_update_settings(plugin_name=plugin_name, config_name=config_name)

    @api_add_rule(
        rule='system/settings/core',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Settings),
    )
    def get_api_settings_core(self):
        """Get or set System Settings > Global settings tab.

        GET: Returns dict of settings and their schema.

        :return: dict or str
        """
        plugin_name = 'core'
        config_name = 'CoreService'
        return self._api_get_settings_json(plugin_name=plugin_name, config_name=config_name)

    @api_add_rule(
        rule='system/settings/core',
        methods=['POST'],
        required_permission=PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings),
    )
    def update_api_settings_core(self):
        """Get or set System Settings > Global settings tab.

        POST: Returns empty str. POST body is dict returned by GET with updated values.

        :return: dict or str
        """
        plugin_name = 'core'
        config_name = 'CoreService'
        return self._api_update_settings(plugin_name=plugin_name, config_name=config_name)

    @api_add_rule(
        rule='system/meta/historical_sizes',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Settings),
    )
    def api_get_historical_size_stats(self):
        """Get disk free, disk usage, and historical data set sizes for Users and Devices.

        GET: Returns dict with keys:
            disk_free: int
            disk_used: int
            entity_sizes: dict with keys
                Devices: dict
                Users: dict

        :return: dict
        """
        return self._get_historical_size_stats()

    @api_add_rule(
        rule='system/meta/about',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Settings),
        enforce_permissions=False,
    )
    def api_get_metadata(self):
        """Get the System Settings > About tab.

        GET: Returns dict with keys:
            Build Date: str
            Installed Version: str
            Customer ID: str
            api_client_version: str

        :return: dict
        """
        obj = {}
        obj.update(self.metadata)
        obj['api_client_version'] = API_CLIENT_VERSION
        return jsonify(obj)

    @api_add_rule(
        rule='system/instances',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Instances),
    )
    def get_api_instances(self):
        """Get instances.

        GET: Returns dict of instances

        :return: dict or str
        """
        return self.get_instances()

    @api_add_rule(
        rule='system/instances',
        methods=['POST'],
        required_permission=PermissionValue.get(PermissionAction.Update, PermissionCategory.Instances),
    )
    def update_api_instances(self):
        """createinstances.

        POST: Returns empty str. Need more details.

        :return: dict or str
        """
        return self.update_instances()

    @api_add_rule(
        rule='system/instances',
        methods=['DELETE'],
        required_permission=PermissionValue.get(PermissionAction.Update, PermissionCategory.Instances),
    )
    def delete_api_instances(self):
        """delete instances.

        DELETE: Returns empty str. Need more details.

        :return: dict or str
        """
        return self.delete_instances()

    @api_add_rule(
        rule='system/discover/lifecycle',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Dashboard),
    )
    def api_get_system_lifecycle(self):
        """Get current status of the system's lifecycle.

        GET returns:
            - All research phases names, for showing the whole picture
            - Current research sub-phase, which is empty if system is not stable
            - Portion of work remaining for the current sub-phase
            - The time next cycle is scheduled to run

        :return: dict
        """
        return jsonify(self._get_system_lifecycle())

    @api_add_rule(
        rule='system/discover/start',
        methods=['POST'],
        required_permission=PermissionValue.get(PermissionAction.RunManualDiscovery, PermissionCategory.Settings),
    )
    def api_schedule_research_phase(self):
        """Start a discover.

        POST: Returns empty str. no body required

        :return: str
        """
        return self._schedule_research_phase()

    @api_add_rule(
        rule='system/discover/stop',
        methods=['POST'],
        required_permission=PermissionValue.get(PermissionAction.RunManualDiscovery, PermissionCategory.Settings),
    )
    def api_stop_research_phase(self):
        """Stop a discover.

        POST: Returns empty str. no body required

        :return: str
        """
        return self._stop_research_phase()

    @paginated()
    @api_add_rule(
        rule='system/users',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.GetUsersAndRoles, PermissionCategory.Settings),
    )
    def get_api_system_users(self, limit, skip):
        """Get users

        GET: Returns list of dict of users.

        :param limit:
        :param skip:
        :return: list of dict or str
        """
        return self._get_user_pages(limit=limit, skip=skip)

    @api_add_rule(
        rule='system/users',
        methods=['PUT'],
        required_permission=PermissionValue.get(
            PermissionAction.Add, PermissionCategory.Settings, PermissionCategory.Users,
        ),
        activity_params=['user_name'])
    def add_api_system_users(self):
        """Add user.

        POST: Returns empty str. Add a user. POST body dict keys:
            user_name: required, str
            password: required, str
            first_name: optional, str
            last_name: optional, str
            role_id: required, str, id of pre-existing role


        :return: list of dict or str
        """
        return self._add_user_wrap()

    @api_add_rule(
        rule='system/users/<user_id>',
        methods=['POST'],
        required_permission=PermissionValue.get(
            PermissionAction.Update, PermissionCategory.Settings, PermissionCategory.Users,
        ),
        activity_params=['user_name'],
    )
    def update_api_system_user(self, user_id):
        """Get users or add user.

        POST: Returns empty str. POST body dict keys:
            first_name: optional, str
            last_name: optional, str
            password: optional, str

        :param user_id:
        :return: str
        """
        return self._update_user(user_id=user_id)

    @api_add_rule(
        'tokens/reset',
        methods=['PUT', 'POST'],
        required_permission=PermissionValue.get(None, PermissionCategory.Settings, PermissionCategory.Users),
    )
    def create_api_reset_password(self):
        """
        Generate a reset password token and link

        POST or PUT (according to the user permission): the body has to contain:
            user_id: str
        :return: The link containing the token
        """
        return self.generate_user_reset_password_link()

    @api_add_rule(
        'tokens/notify',
        methods=['PUT', 'POST'],
        required_permission=PermissionValue.get(None, PermissionCategory.Settings, PermissionCategory.Users),
    )
    def send_api_reset_password_email(self):
        """
        Send a reset password link to a new on an exist user

        POST or PUT (according to the user permission): the body has to contain:
            user_id: str - the user id to reset it's password
            email: str - the email to send the mail to
            invite: str - is it a new user
        :return:
        """
        return self.send_reset_password()

    @api_add_rule(
        rule='system/users/<user_id>',
        methods=['DELETE'],
        required_permission=PermissionValue.get(
            PermissionAction.Delete, PermissionCategory.Settings, PermissionCategory.Users,
        ),
    )
    def api_delete_user(self, user_id):
        """Delete user.

        DELETE: Returns empty str. No body required.

        :param user_id:
        :return: str
        """
        return self.delete_user(user_id=user_id)

    @api_add_rule(
        rule='system/roles/labels',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.GetUsersAndRoles, PermissionCategory.Settings),
    )
    def get_api_roles_labels(self):
        """Get the permissions structure.

        jim: 3.3: added so API client can automatically figure out valid permissions

        :return: dict
        """
        return jsonify(self._get_labels())

    @api_add_rule(
        rule='system/roles',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.GetUsersAndRoles, PermissionCategory.Settings),
    )
    def get_api_roles(self):
        """Get, add, update, or delete roles.

        GET: returns list of dict

        :return: list of dict or str
        """
        return self.get_roles()

    @api_add_rule(
        rule='system/roles',
        methods=['PUT'],
        required_permission=PermissionValue.get(
            PermissionAction.Add, PermissionCategory.Settings, PermissionCategory.Roles,
        ),
    )
    def add_api_roles(self):
        """
        add roles

            name: required, str, name of role
            permissions: required, dict, PermissionCategory with a dict of PermissionCateogry or PermissionAction,
            the permission values are booleans:
                    {
                        PermissionCategory.settings: {
                            PermissionAction.View: True,
                            PermissionCategory.Users: {
                                PermissionAction.Add: True,
                                PermissionAction.Edit: False,
                            },
                            ...
                        }
                    }
        :return: dict of the role
        """
        return self.add_role()

    @api_add_rule(
        rule='system/roles/<role_id>',
        methods=['POST'],
        required_permission=PermissionValue.get(
            PermissionAction.Update, PermissionCategory.Settings, PermissionCategory.Roles,
        ),
    )
    def update_api_roles(self, role_id):
        """add, update, or delete roles.

        PUT: returns empty str, add new role. PUT body dict keys:
            name: required, str, name of role
            permissions: required, dict, values must be one of ["Restricted", "ReadWrite", "ReadOnly"] for keys:
                Adapters: required, str, valid permission name
                Dashboard: required, str, valid permission name
                Devices: required, str, valid permission name
                Enforcements: required, str, valid permission name
                Instances: required, str, valid permission name
                Reports: required, str, valid permission name
                Settings: required, str, valid permission name
                Users: required, str, valid permission name

        :return: dict of the role
        """
        return self.update_role(role_id)

    @api_add_rule(
        rule='system/roles/<role_id>',
        methods=['DELETE'],
        required_permission=PermissionValue.get(
            PermissionAction.Delete, PermissionCategory.Settings, PermissionCategory.Roles,
        ),
    )
    def delete_api_roles(self, role_id):
        return self.delete_roles(role_id)

    ###########
    # ASSETS  #
    ###########

    def api_get_assets_cursor(self,
                              entity_type: EntityType,
                              limit: int,
                              skip: int,
                              mongo_filter: dict,
                              mongo_sort: dict,
                              mongo_projection: dict,
                              history_date: datetime,
                              ) -> dict:
        """Get assets using mongo cursor for paging.

        Request body:
            limit: int
                default: 2000
                max: 2000
                min: 0
                number of rows to return
                @paginated parses as int into limit arg
            skip: int
                default: 0
                min: 0
                number of rows to skip
                @paginated parses as int into skip arg
            filter: str
                default: None
                AQL string
                @filtered_entities parses as dict into mongo_filter arg
            history_date: str
                default: None
                example: 2020-05-18T03:36:14.091000
                datetime to get assets for
                @historical parses into datetime obj as history_date arg
                @filtered_entities parses as dict into mongo_filter arg
            sort: str
                default: None
                field to sort assets on
                @sorted_endpoint parses as dict into mongo_sort arg
            desc: str
                default: None
                example: '1'
                sort descending if '1', asscending if not
                @sorted_endpoint parses as dict into mongo_sort arg
            fields: str
                default: None
                CSV of fields to return
                @projected parses into dict as mongo_projection arg
            cursor: str
                default: None
                UUID of cursor to continue
                get_entities() handles
            include_details: bool
                default: False
                include breakdown of adapter sources for agg data
                get_entities() handles

        Response Body:
            assets: list of dict
            cursor: str
                UUID that tracks iterator for a query
            page: dict
                number: int
                    current page number
                size: int
                    count of assets in this page
                totalPages: int
                    total number of pages
                totalResources: int
                    total number of assets
        """
        request_data = self.get_request_data_as_object() if request.method == 'POST' else request.args

        self._save_query_to_history(
            entity_type=entity_type,
            view_filter=mongo_filter,
            skip=skip,
            limit=limit,
            sort=mongo_sort,
            projection=mongo_projection,
        )

        entities, cursor_obj = get_entities(
            limit=limit,
            skip=skip,
            view_filter=mongo_filter,
            sort=mongo_sort,
            projection=mongo_projection,
            entity_type=entity_type,
            default_sort=self._system_settings.get('defaultSort'),
            include_details=request_data.get('include_details', False),
            cursor_id=request_data.get('cursor', None),
            use_cursor=True,
            history_date=history_date,
        )

        assets = [asset for asset in islice(entities, limit)]
        page_meta = {
            'number': cursor_obj.page_number,
            'size': len(assets),
            'totalPages': math.ceil(cursor_obj.asset_count / limit) if (limit and cursor_obj.asset_count) else 0,
            'totalResources': cursor_obj.asset_count
        }
        return_doc = {'page': page_meta, 'cursor': cursor_obj.cursor_id, 'assets': assets}
        return return_doc

    def api_get_assets_normal(self,
                              entity_type: EntityType,
                              limit: int,
                              skip: int,
                              mongo_filter: dict,
                              mongo_sort: dict,
                              mongo_projection: dict,
                              history_date: datetime,
                              ) -> dict:
        """Get assets using paging.

        Request body:
            limit: int
                default: 2000
                max: 2000
                min: 0
                number of rows to return
                @paginated parses as int into limit arg
            skip: int
                default: 0
                min: 0
                number of rows to skip
                @paginated parses as int into skip arg
            filter: str
                default: None
                AQL string
                @filtered_entities parses as dict into mongo_filter arg
            history_date: str
                default: None
                example: 2020-05-18T03:36:14.091000
                datetime to get assets for
                @historical parses into datetime obj as history_date arg
                @filtered_entities parses as dict into mongo_filter arg
            sort: str
                default: None
                field to sort assets on
                @sorted_endpoint parses as dict into mongo_sort arg
            desc: str
                default: None
                example: '1'
                sort descending if '1', asscending if not
                @sorted_endpoint parses as dict into mongo_sort arg
            fields: str
                default: None
                CSV of fields to return
                @projected parses into dict as mongo_projection arg
            include_details: bool
                default: False
                include breakdown of adapter sources for agg data
                get_entities() handles

        Response Body:
            assets: list of dict
            page: dict
                number: int
                    current page number
                size: int
                    count of assets in this page
                totalPages: int
                    total number of pages
                totalResources: int
                    total number of assets
        """
        request_data = self.get_request_data_as_object() if request.method == 'POST' else request.args

        self._save_query_to_history(
            entity_type=entity_type,
            view_filter=mongo_filter,
            skip=skip,
            limit=limit,
            sort=mongo_sort,
            projection=mongo_projection,
        )

        asset_count = self.api_get_assets_count(
            entity_type=entity_type,
            mongo_filter=mongo_filter,
            history_date=history_date,
        )

        assets = get_entities(
            limit=limit,
            skip=skip,
            view_filter=mongo_filter,
            sort=mongo_sort,
            projection=mongo_projection,
            entity_type=entity_type,
            default_sort=self._system_settings.get('defaultSort'),
            include_details=request_data.get('include_details', False),
            history_date=history_date,
        )

        assets = list(assets)
        page_meta = get_page_metadata(skip=skip, limit=limit, number_of_assets=asset_count)
        page_meta['size'] = len(assets)
        return_doc = {'page': page_meta, 'assets': assets}
        return return_doc

    def api_get_assets_count(self, entity_type: EntityType, mongo_filter: dict, history_date: datetime) -> int:
        """Get the count of assets matching a query.

        Request body:
            filter: str
                default: None
                AQL string
                @filtered_entities parses as dict into mongo_filter arg
            history_date: str
                default: None
                example: 2020-05-18T03:36:14.091000
                datetime to get assets for
                @historical parses into datetime obj as history_date arg

        Response Body:
            str

        APIv2: needs to be proper json response
        """
        entity_collection, is_date_filter_required = self.get_appropriate_view(
            historical=history_date, entity_type=entity_type
        )

        asset_count = get_entities_count(
            entities_filter=mongo_filter,
            entity_collection=entity_collection,
            history_date=history_date,
            is_date_filter_required=is_date_filter_required,
        )
        return asset_count

    def _destroy_assets(self, entity_type, historical_prefix):
        """Delete all assets and optionally all historical assets.

        Will not be usable if 'enable_destroy' is not True in system settings!

        Request Body:
            destroy: bool
                default: False
                Actually do the destroy - must supply True to actually perform this!
                User Fault Protection from random access to this endpoint.
            history: bool
                default: False
                Also destroy all historical data

        Response Body:
            removed: int
                count of assets destroyed
            removed_history: int
                count of all historical assets destroyed

        """
        core_config, _ = self._get_plugin_configs(plugin_unique_name='core', config_name='CoreService')
        api_settings = core_config.get('api_settings', {})
        destroy_enabled = api_settings.get('enable_destroy', False)

        if not destroy_enabled:
            err = f'Global Settings > API Settings > Enable API Destroy Endpoints must be enabled!'
            return return_error(error_message=err, http_status=400, additional_data={'api_settings': api_settings})

        request_data = self.get_request_data_as_object()

        do_destroy = request_data.get('destroy', False)
        do_history = request_data.get('history', False)

        if do_destroy is not True:
            err = f'Must supply destroy=True!'
            return return_error(error_message=err, http_status=400, additional_data=None)

        self._stop_research_phase()

        return_doc = {'removed_history': 0, 'removed': 0}

        if do_history is True:
            collection_names = self.aggregator_db_connection.list_collection_names()
            historical_collection_names = [x for x in collection_names if x.startswith(historical_prefix)]

            for historical_collection_name in historical_collection_names:
                historical_collection = self.aggregator_db_connection[historical_collection_name]
                return_doc['removed_history'] += historical_collection.count() or 0
                historical_collection.drop()

        collection = self._entity_db_map[entity_type]
        return_doc['removed'] += collection.count() or 0
        collection.drop()

        self._insert_indexes_entity(entity_type=entity_type)
        return return_doc

    def _entity_by_id(self, entity_type: EntityType, entity_id):
        """
        Create response expected from single entity api endpoint (not broken by feature AX-3867

        """
        entity_data = get_entity_data(entity_type, entity_id)
        if not isinstance(entity_data, dict):
            return entity_data
        return jsonify({
            'specific': entity_data['adapters'],
            'generic': {
                'basic': entity_data['basic'],
                'data': entity_data['data'],
                'advanced': [{
                    'name': item['schema']['name'], 'data': item['data']
                } for item in entity_data['advanced']]
            },
            'labels': entity_data['labels'],
            'accurate_for_datetime': entity_data['updated'],
            'internal_axon_id': entity_id,
            'tasks': entity_tasks(entity_id)
        })

    ###########
    # DEVICES #
    ###########

    @historical()
    @paginated()
    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @api_add_rule(rule='devices', methods=['GET', 'POST'], required_permission=DEVICE_ASSETS_VIEW)
    def api_devices(self,
                    limit: int,
                    skip: int,
                    mongo_filter: dict,
                    mongo_sort: dict,
                    mongo_projection: dict,
                    history: datetime,
                    ):
        """Get device assets using paging. See api_get_assets_normal docstring."""
        return jsonify(self.api_get_assets_normal(
            entity_type=EntityType.Devices,
            limit=limit,
            skip=skip,
            mongo_filter=mongo_filter,
            mongo_sort=mongo_sort,
            mongo_projection=mongo_projection,
            history_date=history,
        ))

    @historical()
    @paginated()
    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @api_add_rule(rule='devices/cached', methods=['GET', 'POST'], required_permission=DEVICE_ASSETS_VIEW)
    def api_devices_cursor(self,
                           limit: int,
                           skip: int,
                           mongo_filter: dict,
                           mongo_sort: dict,
                           mongo_projection: dict,
                           history: datetime,
                           ):
        """Get device assets using mongo cursor for paging. See api_get_assets_cursor docstring."""
        return jsonify(self.api_get_assets_cursor(
            entity_type=EntityType.Devices,
            limit=limit,
            skip=skip,
            mongo_filter=mongo_filter,
            mongo_sort=mongo_sort,
            mongo_projection=mongo_projection,
            history_date=history,
        ))

    @api_add_rule(rule='devices/history_dates', methods=['GET'], required_permission=DEVICE_ASSETS_VIEW)
    def api_devices_history_dates(self):
        """Get all of the history dates that are valid for devices."""
        return jsonify(all_historical_dates()['devices'])

    @filtered_entities()
    @historical()
    @api_add_rule(rule='devices/count', methods=['GET', 'POST'], required_permission=DEVICE_ASSETS_VIEW)
    def api_devices_count(self, mongo_filter: dict, history: datetime):
        """Get count of device assets. See api_get_assets_count docstring."""
        return str(self.api_get_assets_count(
            entity_type=EntityType.Devices,
            mongo_filter=mongo_filter,
            history_date=history,
        ))

    @api_add_rule(rule='devices/fields', methods=['GET'], required_permission=DEVICE_ASSETS_VIEW)
    def api_devices_fields(self):
        return jsonify(entity_fields(EntityType.Devices))

    @api_add_rule(rule='devices/<device_id>', methods=['GET'], required_permission=DEVICE_ASSETS_VIEW)
    def api_device_by_id(self, device_id):
        return self._entity_by_id(EntityType.Devices, device_id)

    @filtered_entities()
    @api_add_rule(rule='devices/labels', methods=['GET'], required_permission=DEVICE_ASSETS_VIEW)
    def api_get_device_labels(self, mongo_filter):
        return self._entity_labels(self.devices_db, self.devices, mongo_filter)

    @filtered_entities()
    @api_add_rule(rule='devices/labels', methods=['POST', 'DELETE'], required_permission=DEVICE_ASSETS_UPDATE)
    def api_update_device_labels(self, mongo_filter):
        return self._entity_labels(self.devices_db, self.devices, mongo_filter)

    @api_add_rule(rule='devices/destroy', methods=['POST'], required_permission=DEVICE_ASSETS_UPDATE)
    def api_devices_destroy(self):
        """Delete all assets and optionally all historical assets."""
        return jsonify(self._destroy_assets(entity_type=EntityType.Devices, historical_prefix='historical_devices_'))

    #########
    # USERS #
    #########

    @historical()
    @paginated()
    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @api_add_rule(rule='users', methods=['GET', 'POST'], required_permission=USER_ASSETS_VIEW)
    def api_users(self,
                  limit: int,
                  skip: int,
                  mongo_filter: dict,
                  mongo_sort: dict,
                  mongo_projection: dict,
                  history: datetime,
                  ):
        """Get user assets using paging. See api_get_assets_normal docstring."""
        return jsonify(self.api_get_assets_normal(
            entity_type=EntityType.Users,
            limit=limit,
            skip=skip,
            mongo_filter=mongo_filter,
            mongo_sort=mongo_sort,
            mongo_projection=mongo_projection,
            history_date=history,
        ))

    @historical()
    @paginated()
    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @api_add_rule(rule='users/cached', methods=['GET', 'POST'], required_permission=USER_ASSETS_VIEW)
    def api_users_cursor(self,
                         limit: int,
                         skip: int,
                         mongo_filter: dict,
                         mongo_sort: dict,
                         mongo_projection: dict,
                         history: datetime,
                         ):
        """Get user assets using mongo cursor for paging. See api_get_assets_cursor docstring."""
        return jsonify(self.api_get_assets_cursor(
            entity_type=EntityType.Users,
            limit=limit,
            skip=skip,
            mongo_filter=mongo_filter,
            mongo_sort=mongo_sort,
            mongo_projection=mongo_projection,
            history_date=history,
        ))

    @api_add_rule(rule='users/history_dates', methods=['GET'], required_permission=USER_ASSETS_VIEW)
    def api_users_history_dates(self):
        """Get all of the history dates that are valid for users."""
        return jsonify(all_historical_dates()['users'])

    @filtered_entities()
    @historical()
    @api_add_rule(rule='users/count', methods=['GET', 'POST'], required_permission=USER_ASSETS_VIEW)
    def api_users_count(self, mongo_filter: dict, history: datetime):
        """Get count of user assets. See api_get_assets_count docstring."""
        return str(self.api_get_assets_count(
            entity_type=EntityType.Users,
            mongo_filter=mongo_filter,
            history_date=history,
        ))

    @api_add_rule(rule='users/fields', methods=['GET'], required_permission=USER_ASSETS_VIEW)
    def api_users_fields(self):
        return jsonify(entity_fields(EntityType.Users))

    @api_add_rule(rule='users/<user_id>', methods=['GET'], required_permission=USER_ASSETS_VIEW)
    def api_user_by_id(self, user_id):
        return self._entity_by_id(EntityType.Users, user_id)

    @filtered_entities()
    @api_add_rule(rule='users/labels', methods=['GET'], required_permission=USER_ASSETS_VIEW)
    def api_get_user_labels(self, mongo_filter):
        return self._entity_labels(self.users_db, self.users, mongo_filter)

    @filtered_entities()
    @api_add_rule(rule='users/labels', methods=['POST', 'DELETE'], required_permission=USER_ASSETS_UPDATE)
    def api_update_user_labels(self, mongo_filter):
        return self._entity_labels(self.users_db, self.users, mongo_filter)

    @api_add_rule(rule='users/destroy', methods=['POST'], required_permission=USER_ASSETS_UPDATE)
    def api_users_destroy(self):
        """Delete all assets and optionally all historical assets."""
        return jsonify(self._destroy_assets(entity_type=EntityType.Users, historical_prefix='historical_users_'))

    ################
    # ENFORCEMENTS #
    ################

    @paginated()
    @filtered()
    @sorted_endpoint()
    @api_add_rule('alerts', methods=['GET', 'PUT', 'DELETE'], required_permission=PermissionValue.get(
        None, PermissionCategory.Enforcements))
    def api_alerts(self, limit, skip, mongo_filter, mongo_sort):
        if request.method == 'GET':
            enforcements = self._get_enforcements(limit, mongo_filter, mongo_sort, skip)
            return_doc = {
                'page': get_page_metadata(skip, limit, len(enforcements)),
                'assets': enforcements
            }
            return jsonify(return_doc)

        if request.method == 'PUT':
            enforcement_to_add = request.get_json(silent=True)
            return self.put_enforcement(enforcement_to_add)

        # Assuming DELETE method
        enforcement_ids = self.get_request_data_as_object()
        enforcement_selection = {
            'ids': enforcement_ids,
            'include': True
        }
        return self.delete_enforcement(enforcement_selection)

    ###########
    # QUERIES #
    ###########
    def get_query_views(self, limit, skip, mongo_filter, mongo_sort, entity_type):
        views = self._get_entity_views(entity_type, limit, skip, mongo_filter, mongo_sort)

        return_doc = {
            'page': get_page_metadata(skip, limit, len(views)),
            'assets': views
        }

        return jsonify(return_doc)

    def update_query_views(self, mongo_filter, entity_type):
        if request.method == 'POST':
            return_doc = self._add_entity_view(entity_type)
        else:
            return_doc = self._delete_entity_views(entity_type, mongo_filter)

        return jsonify(return_doc)

    @paginated()
    @filtered()
    @sorted_endpoint()
    @api_add_rule('devices/views', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.DevicesAssets))
    def api_get_device_views(self, limit, skip, mongo_filter, mongo_sort):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self.get_query_views(limit, skip, mongo_filter, mongo_sort, EntityType.Devices)

    @filtered()
    @api_add_rule('devices/views', methods=['POST', 'DELETE'],
                  required_permission=PermissionValue.get(None, PermissionCategory.DevicesAssets,
                                                          PermissionCategory.SavedQueries))
    def api_update_device_views(self, mongo_filter):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self.update_query_views(mongo_filter, EntityType.Devices)

    @paginated()
    @filtered()
    @sorted_endpoint()
    @api_add_rule('users/views', methods=['GET'], required_permission=PermissionValue.get(
        None, PermissionCategory.UsersAssets))
    def api_get_users_views(self, limit, skip, mongo_filter, mongo_sort):
        """
        Save or fetch views over the users db
        :return:
        """
        return self.get_query_views(limit, skip, mongo_filter, mongo_sort, EntityType.Users)

    @filtered()
    @api_add_rule('users/views', methods=['POST', 'DELETE'],
                  required_permission=PermissionValue.get(None, PermissionCategory.UsersAssets,
                                                          PermissionCategory.SavedQueries))
    def api_update_users_views(self, mongo_filter):
        """
        Save or fetch views over the users db
        :return:
        """
        return self.update_query_views(mongo_filter, EntityType.Users)

    ###########
    # ACTIONS #
    ###########

    @filtered()
    @api_add_rule('actions/<action_type>', methods=['POST'], required_permission=PermissionValue.get(
        None, PermissionCategory.DevicesAssets))
    def api_run_actions(self, action_type, mongo_filter):
        """
        Executes a run shell command on devices.
        Expected values: a list of internal axon ids, the action name, and the action command.
        :return:
        """

        if action_type == 'upload_file':
            return self._upload_file(DEVICE_CONTROL_PLUGIN_NAME)

        action_data = self.get_request_data_as_object()
        action_data['action_type'] = action_type
        action_data['entities'] = {
            'ids': action_data['internal_axon_ids'],
            'include': True,
        }
        return self.run_actions(action_data, mongo_filter)

    @api_add_rule('actions', required_permission=PermissionValue.get(
        PermissionAction.View, PermissionCategory.DevicesAssets))
    def api_get_actions(self):
        """
        Executes a run shell command on devices.
        Expected values: a list of internal axon ids, the action name, and the action command.
        :return:
        """
        actions = ['deploy', 'shell', 'upload_file']
        return jsonify(actions)

    ############
    # ADAPTERS #
    ############

    # jim:3.0
    @api_add_rule(
        rule='adapters/<plugin_name>/config/<config_name>',
        methods=['GET'],
        required_permission=PermissionValue.get(PermissionAction.View, PermissionCategory.Settings),
    )
    def api_get_adapter_config(self, plugin_name, config_name):
        """Get a specific config on a specific adapter.

        :return: dict or str
        """
        config_obj, config_schema = self._get_plugin_configs(plugin_unique_name=plugin_name, config_name=config_name)
        return jsonify({'config': config_obj, 'schema': config_schema})

    @api_add_rule(
        rule='adapters/<plugin_name>/config/<config_name>',
        methods=['POST'],
        required_permission=PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings),
    )
    def api_update_adapter_config(self, plugin_name, config_name):
        """Set a specific config on a specific adapter.

        :return: dict or str
        """
        return self._save_plugin_config(plugin_unique_name=plugin_name, config_name=config_name)

    @api_add_rule('adapters/<adapter_name>/clients', methods=['PUT', 'POST'], required_permission=PermissionValue.get(
        None, PermissionCategory.Adapters, PermissionCategory.Connections))
    def api_adapters_clients(self, adapter_name):
        request_data = self.get_request_data_as_object()
        if not request_data:
            return return_error('Connection data is required', 400)
        instance_id = request_data.pop('instanceName', self.node_id)
        connection_label = request_data.pop('connection_label', None)
        connection_data = {
            'connection': request_data,
            'connection_label': connection_label
        }
        if request.method == 'PUT':
            return self._add_connection(adapter_name, instance_id, connection_data)
        return self._test_connection(adapter_name, instance_id, request_data)

    @api_add_rule('adapters/<adapter_name>/<node_id>/upload_file', methods=['POST'],
                  required_permission=PermissionValue.get(None, PermissionCategory.Adapters),
                  skip_activity=True)
    def api_adapter_upload_file(self, adapter_name, node_id):
        adapter_unique_name = self.request_remote_plugin(
            f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}'
        )
        adapter_unique_name = adapter_unique_name.json().get('plugin_unique_name')
        ret = self._upload_file(adapter_unique_name)
        return ret

    @api_add_rule('adapters', methods=['GET'], required_permission=PermissionValue.get(
        None, PermissionCategory.Adapters))
    def api_adapters(self):
        adapters = self._adapters()
        for adapter_name in adapters.keys():
            for adapter in adapters[adapter_name]:
                for client in adapter['clients']:
                    client_label = self.adapter_client_labels_db.find_one({
                        'client_id': client['client_id'],
                        PLUGIN_NAME: adapter_name,
                        NODE_ID: adapter[NODE_ID]
                    }, {
                        CONNECTION_LABEL: 1
                    })
                    client['client_config'][CONNECTION_LABEL] = (client_label.get(CONNECTION_LABEL, '')
                                                                 if client_label else '')
        return jsonify(adapters)

    @api_add_rule('adapters/<adapter_name>/clients/<client_id>', methods=['PUT', 'DELETE'],
                  required_permission=PermissionValue.get(None,
                                                          PermissionCategory.Adapters,
                                                          PermissionCategory.Connections))
    def api_adapters_clients_update(self, adapter_name, client_id=None):
        request_data = self.get_request_data_as_object()
        if not request_data:
            return return_error('Connection data is required', 400)
        instance_id = request_data.pop('instanceName', self.node_id)
        prev_instance_id = request_data.pop('oldInstanceName', None)
        connection_label = request_data.pop('connection_label', None)
        connection_data = {
            'connection': request_data,
            'connection_label': connection_label
        }
        return self._update_connection(client_id, adapter_name, instance_id, prev_instance_id, connection_data)

    ##############
    # COMPLIANCE #
    ##############

    @accounts_filter()
    @api_add_rule('compliance/<compliance_name>/<method>', methods=['GET', 'POST'],
                  required_permission=PermissionValue.get(None, PermissionCategory.Compliance))
    def api_get_compliance(self, compliance_name, method, accounts):
        response = self._get_compliance(compliance_name, method, accounts)
        response_dict = json.loads(response.data)
        return jsonify(response_dict.get('rules', []))

    @accounts_filter()
    @schema()
    @api_add_rule('compliance/<compliance_name>/csv', methods=['POST'], required_permission=PermissionValue.get(
        PermissionAction.Update, PermissionCategory.Compliance))
    def api_post_compliance_csv(self, compliance_name, schema_fields, accounts):
        return self._post_compliance_csv(compliance_name, schema_fields, accounts)
