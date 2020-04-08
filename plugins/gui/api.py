import logging
import math
from itertools import islice
from typing import Iterable

from flask import jsonify, request, has_request_context, g
from passlib.hash import bcrypt

from axonius.consts.gui_consts import IS_AXONIUS_ROLE
from axonius.consts.metric_consts import ApiMetric
from axonius.consts.plugin_consts import DEVICE_CONTROL_PLUGIN_NAME
from axonius.logging.metric_helper import log_metric
from axonius.plugin_base import EntityType, return_error, PluginBase
from axonius.utils.db_querying_helper import get_entities
from axonius.utils.gui_helpers import (accounts as accounts_filter,
                                       schema_fields as schema,
                                       paginated, filtered_entities,
                                       sorted_endpoint, projected, filtered,
                                       add_rule_custom_authentication,
                                       get_entities_count, add_rule_unauth,
                                       entity_fields, PAGINATION_LIMIT_MAX)
from axonius.utils.permissions_helper import (PermissionCategory, PermissionAction,
                                              PermissionValue, deserialize_db_permissions, is_axonius_role)
from axonius.utils.metric import remove_ids
from gui.logic.entity_data import (get_entity_data, entity_tasks)
from gui.logic.routing_helper import check_permissions

logger = logging.getLogger(f'axonius.{__name__}')

API_VERSION = '1'


# pylint: disable=protected-access,no-self-use,no-member

# Caution! These decorators must come BEFORE @add_rule


def basic_authentication(func, required_permission_values: Iterable[PermissionValue] = None):
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
                return None
            role = roles_collection.find_one({'_id': user_from_db.get('role_id')})
            if not bcrypt.verify(password, user_from_db['password']):
                return None
            if (PluginBase.Instance.trial_expired() or PluginBase.Instance.contract_expired())\
                    and not role.get(IS_AXONIUS_ROLE):
                return None

            if user_from_db.get('name') == 'admin':
                return user_from_db
            if not check_permissions(deserialize_db_permissions(role['permissions']),
                                     required_permission_values,
                                     request.method):
                return None
            return user_from_db

        def check_auth_api_key(api_key, api_secret):
            """
            This function is called to check if an api key and secret match
            """
            user_from_db = users_collection.find_one({
                'api_key': api_key,
                'api_secret': api_secret
            })

            if not user_from_db:
                return None
            role = roles_collection.find_one({'_id': user_from_db.get('role_id')})
            if (PluginBase.Instance.trial_expired() or PluginBase.Instance.contract_expired()) \
                    and not is_axonius_role(role):
                return None
            if user_from_db.get('admin'):
                return user_from_db
            role = roles_collection.find_one({'_id': user_from_db.get('role_id')})
            if not check_permissions(deserialize_db_permissions(role['permissions']),
                                     required_permission_values,
                                     request.method):
                return None
            return user_from_db

        api_auth = request.headers.get('api-key'), request.headers.get('api-secret')
        auth = request.authorization
        user_from_db = check_auth_api_key(*api_auth) or (auth and check_auth_user(auth.username, auth.password))
        if user_from_db:

            if has_request_context():
                path = request.path
                cleanpath = remove_ids(path)
                log_metric(logger, ApiMetric.PUBLIC_REQUEST_PATH, cleanpath, method=request.method)

            # save the associated user for the local request
            g.api_request_user = user_from_db

            return func(self, *args, **kwargs)

        return return_error('Unauthorized', 401)

    return wrapper


def api_add_rule(rule, *args,
                 required_permission_values: Iterable[PermissionValue] = None, **kwargs):
    """
    A URL mapping for API endpoints that use the API method to log in (either user and pass or API key)
    """

    def basic_authentication_permissions(*args, **kwargs):
        return basic_authentication(*args, **kwargs,
                                    required_permission_values=required_permission_values)

    return add_rule_custom_authentication(f'V{API_VERSION}/{rule}', basic_authentication_permissions, *args, **kwargs)


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

    # jim:3.0
    ##########
    # SYSTEM #
    ##########

    @api_add_rule(
        'system/settings/lifecycle',
        methods=['GET'],
        required_permission_values={
            PermissionValue.get(PermissionAction.View, PermissionCategory.Settings)
        },
    )
    def get_api_settings_lifecycle(self):
        """Get or set System Settings > Lifecycle settings tab.

        GET: Returns dict of settings and their schema.

        :return: dict or str
        """
        return self.get_plugin_configs(
            plugin_name='system_scheduler', config_name='SystemSchedulerService'
        )

    @api_add_rule(
        'system/settings/lifecycle',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings)
        },
    )
    def update_api_settings_lifecycle(self):
        """Get or set System Settings > Lifecycle settings tab.

        POST: Returns empty str. POST body is dict returned by GET with updated values.

        :return: dict or str
        """
        return self.update_plugin_configs(
            plugin_name='system_scheduler', config_name='SystemSchedulerService'
        )

    @api_add_rule(
        'system/settings/gui',
        methods=['GET'],
        required_permission_values={
            PermissionValue.get(PermissionAction.View, PermissionCategory.Settings)
        },
    )
    def get_api_settings_gui(self):
        """Get or set System Settings > GUI settings tab.

        GET: Returns dict of settings and their schema.

        :return: dict or str
        """
        return self.get_plugin_configs(
            plugin_name='gui', config_name='GuiService'
        )

    @api_add_rule(
        'system/settings/gui',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings)
        },
    )
    def update_api_settings_gui(self):
        """Get or set System Settings > GUI settings tab.

        POST: Returns empty str. POST body is dict returned by GET with updated values.

        :return: dict or str
        """
        return self.update_plugin_configs(
            plugin_name='gui', config_name='GuiService'
        )

    @api_add_rule(
        'system/settings/core',
        methods=['GET'],
        required_permission_values={
            PermissionValue.get(PermissionAction.View, PermissionCategory.Settings)
        },
    )
    def get_api_settings_core(self):
        """Get or set System Settings > Global settings tab.

        GET: Returns dict of settings and their schema.

        :return: dict or str
        """
        return self.get_plugin_configs(
            plugin_name='core', config_name='CoreService'
        )

    @api_add_rule(
        'system/settings/core',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings)
        },
    )
    def update_api_settings_core(self):
        """Get or set System Settings > Global settings tab.

        POST: Returns empty str. POST body is dict returned by GET with updated values.

        :return: dict or str
        """
        return self.update_plugin_configs(
            plugin_name='core', config_name='CoreService'
        )

    @api_add_rule(
        'system/meta/historical_sizes',
        methods=['GET'],
        required_permission_values={
            PermissionValue.get(PermissionAction.View, PermissionCategory.Settings)
        },
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
        'system/meta/about',
        methods=['GET'],
        required_permission_values={
            PermissionValue.get(PermissionAction.View, PermissionCategory.Settings)
        },
    )
    def api_get_metadata(self):
        """Get the System Settings > About tab.

        GET: Returns dict with keys:
            Build Date: str
            Commit Date: str
            Commit Hash: str
            Version: str

        :return: dict
        """
        return jsonify(self.metadata)

    @api_add_rule(
        'system/instances',
        methods=['GET'],
        required_permission_values={
            PermissionValue.get(PermissionAction.View, PermissionCategory.Instances)
        },
    )
    def get_api_instances(self):
        """Get instances.

        GET: Returns dict of instances

        :return: dict or str
        """
        return self.get_instances()

    @api_add_rule(
        'system/instances',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Update, PermissionCategory.Instances)
        },
    )
    def update_api_instances(self):
        """createinstances.

        POST: Returns empty str. Need more details.

        :return: dict or str
        """
        return self.update_instances()

    @api_add_rule(
        'system/instances',
        methods=['DELETE'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Update, PermissionCategory.Instances)
        },
    )
    def delete_api_instances(self):
        """delete instances.

        DELETE: Returns empty str. Need more details.

        :return: dict or str
        """
        return self.delete_instances()

    @api_add_rule(
        'system/discover/lifecycle',
        methods=['GET'],
        required_permission_values={
            PermissionValue.get(PermissionAction.View, PermissionCategory.Dashboard)
        },
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
        f'system/discover/start',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.RunManualDiscovery, PermissionCategory.Settings)
        },
    )
    def api_schedule_research_phase(self):
        """Start a discover.

        POST: Returns empty str. no body required

        :return: str
        """
        return self._schedule_research_phase()

    @api_add_rule(
        'system/discover/stop',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.RunManualDiscovery, PermissionCategory.Settings)
        },
    )
    def api_stop_research_phase(self):
        """Stop a discover.

        POST: Returns empty str. no body required

        :return: str
        """
        return self._stop_research_phase()

    @paginated()
    @api_add_rule(
        'system/users',
        methods=['GET'],
        required_permission_values={
            PermissionValue.get(PermissionAction.GetUsersAndRoles, PermissionCategory.Settings)
        },
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
        'system/users',
        methods=['PUT'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Add, PermissionCategory.Settings, PermissionCategory.Users)
        },
    )
    def update_api_system_users(self):
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
        'system/users/<user_id>',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings, PermissionCategory.Users)
        },
    )
    def api_update_user(self, user_id):
        """Get users or add user.

        POST: Returns empty str. POST body dict keys:
            first_name: optional, str
            last_name: optional, str
            password: optional, str

        :param user_id:
        :return: str
        """
        return self.update_user(user_id=user_id)

    @api_add_rule(
        'system/users/<user_id>',
        methods=['DELETE'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Delete, PermissionCategory.Settings, PermissionCategory.Users)
        },
    )
    def api_delete_user(self, user_id):
        """Delete user.

        DELETE: Returns empty str. No body required.

        :param user_id:
        :return: str
        """
        return self.delete_user(user_id=user_id)

    @api_add_rule(
        'system/roles/default',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings, PermissionCategory.Users)
        },
    )
    def update_api_roles_default(self):
        """Set the default role for externally created users.

        POST: Returns empty str. POST body dict keys:
            name: required, str, name of role to set as default

        :return: str
        """
        return self.update_roles_default()

    @api_add_rule(
        'system/roles',
        methods=['GET'],
        required_permission_values={
            PermissionValue.get(PermissionAction.GetUsersAndRoles, PermissionCategory.Settings)
        },
    )
    def get_api_roles(self):
        """Get, add, update, or delete roles.

        GET: returns list of dict

        :return: list of dict or str
        """
        return self.get_roles()

    @api_add_rule(
        'system/roles',
        methods=['PUT'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Add, PermissionCategory.Settings, PermissionCategory.Roles)
        },
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
        'system/roles/<role_id>',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings, PermissionCategory.Roles)
        },
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
        'system/roles/<role_id>',
        methods=['DELETE'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Delete, PermissionCategory.Settings, PermissionCategory.Roles)
        },
    )
    def delete_api_roles(self, role_id):
        return self.delete_roles(role_id)

    ###########
    # DEVICES #
    ###########
    @add_rule_unauth(f'api')
    def api_description(self):
        return API_VERSION

    @paginated()
    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @api_add_rule(f'devices', methods=['GET', 'POST'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.DevicesAssets)})
    def api_devices(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        devices_collection = self._entity_db_map[EntityType.Devices]
        self._save_query_to_history(EntityType.Devices, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        return_doc = {
            'page': get_page_metadata(skip, limit,
                                      get_entities_count(mongo_filter, devices_collection)),
            'assets': list(get_entities(limit, skip, mongo_filter, mongo_sort,
                                        mongo_projection,
                                        EntityType.Devices,
                                        default_sort=self._system_settings['defaultSort']))
        }

        return jsonify(return_doc)

    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @api_add_rule(f'devices/cached', methods=['GET', 'POST'],
                  required_permission_values={
                      PermissionValue.get(PermissionAction.View, PermissionCategory.DevicesAssets)})
    def api_cached_devices(self, mongo_filter, mongo_sort, mongo_projection):
        content = self.get_request_data_as_object() if request.method == 'POST' else request.args
        assets_count = None
        try:
            limit = int(content.get('limit', PAGINATION_LIMIT_MAX))
            if limit < 1 or limit > PAGINATION_LIMIT_MAX:
                limit = PAGINATION_LIMIT_MAX
        except Exception:
            limit = PAGINATION_LIMIT_MAX
        cursor_id = content.get('cursor')
        # count filtered assets only on the first request.
        if not cursor_id:
            devices_collection = self._entity_db_map[EntityType.Devices]
            assets_count = get_entities_count(mongo_filter, devices_collection)

        data, cursor_id = get_entities(0, 0, mongo_filter, mongo_sort,
                                       mongo_projection,
                                       EntityType.Devices,
                                       default_sort=self._system_settings['defaultSort'], cursor_id=cursor_id,
                                       use_cursor=True)
        assets = [asset for asset in islice(data, limit)]
        return_doc = {
            'page': {
                'totalResources': assets_count,
                'size': len(assets)
            },
            'cursor': cursor_id,
            'assets': assets
        }
        return jsonify(return_doc)

    @filtered_entities()
    @api_add_rule(f'devices/count', methods=['GET', 'POST'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.DevicesAssets)})
    def api_devices_count(self, mongo_filter):
        return str(get_entities_count(mongo_filter, self._entity_db_map[EntityType.Devices]))

    @api_add_rule(
        f'devices/fields',
        required_permission_values={
            PermissionValue.get(PermissionAction.View, PermissionCategory.DevicesAssets)
        })
    def api_devices_fields(self):
        return jsonify(entity_fields(EntityType.Devices))

    @api_add_rule(f'devices/<device_id>',
                  required_permission_values={
                      PermissionValue.get(PermissionAction.View, PermissionCategory.DevicesAssets)})
    def api_device_by_id(self, device_id):
        return self._entity_by_id(EntityType.Devices, device_id)

    @filtered_entities()
    @api_add_rule('devices/labels', methods=['GET'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.DevicesAssets)})
    def api_get_device_labels(self, mongo_filter):
        return self._entity_labels(self.devices_db, self.devices, mongo_filter)

    @filtered_entities()
    @api_add_rule('devices/labels', methods=['POST', 'DELETE'],
                  required_permission_values={
                      PermissionValue.get(PermissionAction.Update, PermissionCategory.DevicesAssets)})
    def api_update_device_labels(self, mongo_filter):
        return self._entity_labels(self.devices_db, self.devices, mongo_filter)

    #########
    # USERS #
    #########

    @paginated()
    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @api_add_rule(f'users', methods=['GET', 'POST'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.UsersAssets)})
    def api_users(self, limit, skip, mongo_filter, mongo_sort, mongo_projection):
        users_collection = self._entity_db_map[EntityType.Users]
        self._save_query_to_history(EntityType.Users, mongo_filter, skip, limit, mongo_sort, mongo_projection)
        return_doc = {
            'page': get_page_metadata(skip, limit, get_entities_count(mongo_filter, users_collection)),
            'assets': list(get_entities(limit, skip, mongo_filter, mongo_sort,
                                        mongo_projection,
                                        EntityType.Users,
                                        default_sort=self._system_settings['defaultSort']))
        }

        return jsonify(return_doc)

    @filtered_entities()
    @sorted_endpoint()
    @projected()
    @api_add_rule(f'users/cached', methods=['GET', 'POST'],
                  required_permission_values={
                      PermissionValue.get(PermissionAction.View, PermissionCategory.UsersAssets)})
    def api_cached_users(self, mongo_filter, mongo_sort, mongo_projection):
        content = self.get_request_data_as_object() if request.method == 'POST' else request.args
        assets_count = None
        try:
            limit = int(content.get('limit', PAGINATION_LIMIT_MAX))
            if limit < 1 or limit > PAGINATION_LIMIT_MAX:
                limit = PAGINATION_LIMIT_MAX
        except Exception:
            limit = PAGINATION_LIMIT_MAX
        cursor_id = content.get('cursor')
        # count filtered assets only on the first request.
        if not cursor_id:
            devices_collection = self._entity_db_map[EntityType.Users]
            assets_count = get_entities_count(mongo_filter, devices_collection)

        data, cursor_id = get_entities(0, 0, mongo_filter, mongo_sort,
                                       mongo_projection,
                                       EntityType.Devices,
                                       default_sort=self._system_settings['defaultSort'], cursor_id=cursor_id,
                                       use_cursor=True)
        assets = [asset for asset in islice(data, limit)]
        return_doc = {
            'page': {
                'totalResources': assets_count,
                'size': len(assets)
            },
            'cursor': cursor_id,
            'assets': assets
        }
        return jsonify(return_doc)

    @filtered_entities()
    @api_add_rule(f'users/count', methods=['GET', 'POST'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.UsersAssets)})
    def api_users_count(self, mongo_filter):
        return str(get_entities_count(mongo_filter, self._entity_db_map[EntityType.Users]))

    @api_add_rule(
        f'users/fields',
        required_permission_values={
            PermissionValue.get(PermissionAction.View, PermissionCategory.UsersAssets)})
    def api_users_fields(self):
        return jsonify(entity_fields(EntityType.Users))

    @api_add_rule(f'users/<user_id>',
                  required_permission_values={
                      PermissionValue.get(PermissionAction.View, PermissionCategory.UsersAssets)
                  })
    def api_user_by_id(self, user_id):
        return self._entity_by_id(EntityType.Users, user_id)

    def _entity_by_id(self, entity_type: EntityType, entity_id):
        """
        Create response expected from single entity api endpoint (not broken by feature AX-3867

        """
        entity_data = get_entity_data(entity_type, entity_id)
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

    @filtered_entities()
    @api_add_rule('users/labels', methods=['GET'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.UsersAssets)})
    def api_get_user_labels(self, mongo_filter):
        return self._entity_labels(self.users_db, self.users, mongo_filter)

    @filtered_entities()
    @api_add_rule('users/labels', methods=['POST', 'DELETE'],
                  required_permission_values={
                      PermissionValue.get(PermissionAction.Update, PermissionCategory.UsersAssets)})
    def api_update_user_labels(self, mongo_filter):
        return self._entity_labels(self.users_db, self.users, mongo_filter)

    ################
    # ENFORCEMENTS #
    ################

    @paginated()
    @filtered()
    @sorted_endpoint()
    @api_add_rule(f'alerts', methods=['GET', 'PUT', 'DELETE'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.Enforcements)})
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
            return_doc = self._update_entity_views(entity_type)
        else:
            return_doc = self._delete_entity_views(entity_type, mongo_filter)

        return jsonify(return_doc)

    @paginated()
    @filtered()
    @sorted_endpoint()
    @api_add_rule(f'devices/views', methods=['GET'],
                  required_permission_values={
                      PermissionValue.get(PermissionAction.View, PermissionCategory.DevicesAssets)})
    def api_get_device_views(self, limit, skip, mongo_filter, mongo_sort):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self.get_query_views(limit, skip, mongo_filter, mongo_sort, EntityType.Devices)

    @filtered()
    @api_add_rule(f'devices/views', methods=['POST', 'DELETE'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.DevicesAssets, PermissionCategory.SavedQueries)})
    def api_update_device_views(self, mongo_filter):
        """
        Save or fetch views over the devices db
        :return:
        """
        return self.update_query_views(mongo_filter, EntityType.Devices)

    @paginated()
    @filtered()
    @sorted_endpoint()
    @api_add_rule(f'users/views', methods=['GET'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.UsersAssets)})
    def api_get_users_views(self, limit, skip, mongo_filter, mongo_sort):
        """
        Save or fetch views over the users db
        :return:
        """
        return self.get_query_views(limit, skip, mongo_filter, mongo_sort, EntityType.Users)

    @filtered()
    @api_add_rule(f'users/views', methods=['POST', 'DELETE'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.UsersAssets, PermissionCategory.SavedQueries)})
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
    @api_add_rule(f'actions/<action_type>', methods=['POST'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.DevicesAssets)})
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

    @api_add_rule(f'actions',
                  required_permission_values={
                      PermissionValue.get(PermissionAction.View, PermissionCategory.DevicesAssets)})
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
        'adapters/<plugin_name>/config/<config_name>',
        methods=['GET'],
        required_permission_values={
            PermissionValue.get(PermissionAction.View, PermissionCategory.Settings)})
    def api_get_adapter_config(self, plugin_name, config_name):
        """Get a specific config on a specific adapter.

        :return: dict or str
        """
        return self.get_plugin_configs(
            plugin_name=plugin_name, config_name=config_name
        )

    @api_add_rule(
        'adapters/<plugin_name>/config/<config_name>',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Update, PermissionCategory.Settings)})
    def api_update_adapter_config(self, plugin_name, config_name):
        """Set a specific config on a specific adapter.

        :return: dict or str
        """
        return self.update_plugin_configs(
            plugin_name=plugin_name, config_name=config_name
        )

    @api_add_rule(f'adapters/<adapter_name>/clients', methods=['PUT', 'POST'],
                  required_permission_values={
                      PermissionValue.get(None,
                                          PermissionCategory.Adapters,
                                          PermissionCategory.Connections)})
    def api_adapters_clients(self, adapter_name):
        return self._adapters_clients(adapter_name)

    @api_add_rule('adapters/<adapter_name>/<node_id>/upload_file', methods=['POST'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.Adapters)})
    def api_adapter_upload_file(self, adapter_name, node_id):
        adapter_unique_name = self.request_remote_plugin(
            f'find_plugin_unique_name/nodes/{node_id}/plugins/{adapter_name}'
        )
        adapter_unique_name = adapter_unique_name.json().get('plugin_unique_name')
        ret = self._upload_file(adapter_unique_name)
        return ret

    @api_add_rule('adapters', methods=['GET'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.Adapters)})
    def api_adapters(self):
        return jsonify(self._adapters())

    @api_add_rule('adapters/<adapter_name>/clients/<client_id>', methods=['PUT', 'DELETE'],
                  required_permission_values={
                      PermissionValue.get(None, PermissionCategory.Adapters, PermissionCategory.Connections)})
    def api_adapters_clients_update(self, adapter_name, client_id=None):
        return self._adapters_clients_update(adapter_name, client_id)

    ##############
    # COMPLIANCE #
    ##############

    @accounts_filter()
    @api_add_rule(
        'compliance/<compliance_name>/<method>',
        methods=['GET', 'POST'],
        required_permission_values={
            PermissionValue.get(None, PermissionCategory.Compliance)}
    )
    def api_get_compliance(self, compliance_name, method, accounts):
        return self._get_compliance(compliance_name, method, accounts)

    @accounts_filter()
    @schema()
    @api_add_rule(
        'compliance/<compliance_name>/csv',
        methods=['POST'],
        required_permission_values={
            PermissionValue.get(PermissionAction.Update, PermissionCategory.Compliance)}
    )
    def api_post_compliance_csv(self, compliance_name, schema_fields, accounts):
        return self._post_compliance_csv(compliance_name, schema_fields, accounts)
