# pylint: disable=too-many-lines
import json
import logging
import os
import re
import secrets
import subprocess
import threading
import time
import configparser

from datetime import datetime, timedelta
from distutils.version import StrictVersion
from multiprocessing.pool import ThreadPool
from typing import (List, Dict)
from pathlib import Path
from bson import ObjectId
from bson.json_util import dumps
import bcrypt
import requests
import cachetools

import pymongo
from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import session, g
# pylint: disable=import-error,no-name-in-module

from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.system_consts import AXONIUS_SAAS_VAR_NAME
from axonius.logging.audit_helper import AuditCategory, AuditAction, AuditType
from axonius.saas.input_params import read_saas_input_params
from axonius.saas.saas_secrets_manager import SaasSecretsManager
from axonius.utils.revving_cache import rev_cached
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.gui_consts import (ENCRYPTION_KEY_PATH,
                                       ROLES_COLLECTION,
                                       TEMP_MAINTENANCE_THREAD_ID,
                                       USERS_COLLECTION,
                                       PROXY_DATA_PATH,
                                       DASHBOARD_SPACES_COLLECTION,
                                       DASHBOARD_COLLECTION,
                                       USERS_PREFERENCES_COLLECTION,
                                       PREDEFINED_ROLE_ADMIN,
                                       PREDEFINED_ROLE_OWNER,
                                       PREDEFINED_ROLE_VIEWER,
                                       PREDEFINED_ROLE_RESTRICTED,
                                       PREDEFINED_FIELD,
                                       PREDEFINED_ROLE_OWNER_RO,
                                       IS_AXONIUS_ROLE,
                                       USERS_TOKENS_COLLECTION, USERS_TOKENS_COLLECTION_TTL_INDEX_NAME,
                                       LATEST_VERSION_URL, INSTALLED_VERISON_KEY, FeatureFlagsNames,
                                       IDENTITY_PROVIDERS_CONFIG, NO_ACCESS_ROLE,
                                       DEFAULT_ROLE_ID, ROLE_ASSIGNMENT_RULES, IS_API_USER, Signup,
                                       PREDEFINED_SAVED_QUERY_REF_REGEX, UPDATED_BY_FIELD,
                                       FEATURE_FLAGS_CONFIG)
from axonius.consts.metric_consts import SystemMetric
from axonius.consts.plugin_consts import (AXONIUS_USER_NAME,
                                          ADMIN_USER_NAME,
                                          GUI_PLUGIN_NAME,
                                          GUI_SYSTEM_CONFIG_COLLECTION,
                                          METADATA_PATH, PLUGIN_NAME, PLUGIN_UNIQUE_NAME, SYSTEM_SETTINGS, PROXY_VERIFY,
                                          CORE_UNIQUE_NAME, NODE_NAME, NODE_USE_AS_ENV_NAME, AXONIUS_RO_USER_NAME,
                                          PASSWORD_SETTINGS, PASSWORD_LENGTH_SETTING, PASSWORD_MIN_LOWERCASE,
                                          PASSWORD_MIN_UPPERCASE, PASSWORD_MIN_NUMBERS, PASSWORD_MIN_SPECIAL_CHARS,
                                          PASSWORD_BRUTE_FORCE_PROTECTION, PASSWORD_PROTECTION_ALLOWED_RETRIES,
                                          PASSWORD_PROTECTION_LOCKOUT_MIN, PASSWORD_PROTECTION_BY_IP,
                                          RESET_PASSWORD_SETTINGS, RESET_PASSWORD_LINK_EXPIRATION,
                                          AXONIUS_SETTINGS_PATH)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.devices.device_adapter import DeviceAdapter
from axonius.logging.metric_helper import log_metric
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import (RunIdentifier,
                                        Triggerable)
from axonius.plugin_base import EntityType, PluginBase, random_string
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.gui_helpers import (get_entities_count, get_connected_user_id, get_entities_count_cached)
from axonius.utils.permissions_helper import (get_admin_permissions, get_viewer_permissions,
                                              is_role_admin, is_axonius_role,
                                              PermissionCategory, PermissionAction, get_permissions_structure,
                                              serialize_db_permissions)
from axonius.utils.proxy_utils import to_proxy_string
from axonius.utils.ssl import MUTUAL_TLS_CA_PATH, \
    MUTUAL_TLS_CONFIG_FILE
from gui.api import APIMixin
from gui.cached_session import CachedSessionInterface
from gui.feature_flags import FeatureFlags
from gui.identity_providers import IdentityProviders
from gui.logic.dashboard_data import (adapter_data)
from gui.logic.login_helper import has_customer_login_happened
from gui.logic.filter_utils import filter_archived
from gui.routes.app_routes import AppRoutes

# pylint: disable=invalid-name,too-many-instance-attributes,inconsistent-return-statements,too-many-statements,no-else-return,no-self-use

logger = logging.getLogger(f'axonius.{__name__}')

SAML_SETTINGS_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config', 'saml_settings.json'))
DEFAULT_AWS_TEST_USER = 'admin2'
DEFAULT_AWS_TEST_PASSWORD = '$2b$12$GE1DJiMkTLh.5VW6iICUr.oR5yVIXgA5vFK1FF2dkHzoNYMYyKecO'
SUPPORTED_API_VERSIONS = ['4.0']


def _generate_password(length=32):
    password = secrets.token_hex(nbytes=length).encode()
    return bcrypt.hashpw(password, bcrypt.gensalt())


class GuiService(Triggerable,
                 FeatureFlags,
                 IdentityProviders,
                 PluginBase,
                 Configurable,
                 APIMixin,
                 AppRoutes):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    class MyUserAdapter(UserAdapter):
        pass

    DEFAULT_AVATAR_PIC = '/src/assets/images/users/avatar.png'
    ALT_AVATAR_PIC = '/src/assets/images/users/alt_avatar.png'
    DEFAULT_USER = {'user_name': ADMIN_USER_NAME,
                    'password': _generate_password(),
                    'first_name': 'administrator', 'last_name': '',
                    'pic_name': DEFAULT_AVATAR_PIC,
                    'source': 'internal',
                    'api_key': secrets.token_urlsafe(),
                    'api_secret': secrets.token_urlsafe(),
                    'password_last_updated': datetime.utcnow()
                    }

    ALTERNATIVE_USER = {'user_name': AXONIUS_USER_NAME,
                        'password': _generate_password(),
                        'first_name': 'axonius', 'last_name': '',
                        'pic_name': ALT_AVATAR_PIC,
                        'source': 'internal',
                        'api_key': secrets.token_urlsafe(),
                        'api_secret': secrets.token_urlsafe()
                        }

    ALTERNATIVE_RO_USER = {'user_name': AXONIUS_RO_USER_NAME,
                           'password': _generate_password(),
                           'first_name': 'axonius_ro', 'last_name': '',
                           'pic_name': ALT_AVATAR_PIC,
                           'source': 'internal',
                           'api_key': secrets.token_urlsafe(),
                           'api_secret': secrets.token_urlsafe()
                           }

    def __create_user_tokens_index(self):
        # add ttl index to user tokens collection if not exist, prior to our logic the ttl value
        # can be set from the setting page, therefore we have to check the existence of the index
        # before applying the default value.
        # setting a different value from the existed value will raise exception
        # we dont take the value from the settings collection because if he exist this mean no index need to be created
        users_tokens_collection_indexes = \
            [x['key'][0][0] for x in self._users_tokens_collection.index_information().values()]

        if USERS_TOKENS_COLLECTION_TTL_INDEX_NAME not in users_tokens_collection_indexes:
            # default is 48 hours in seconds
            default_ttl = 60 * 60 * 48
            self._users_tokens_collection.create_index(USERS_TOKENS_COLLECTION_TTL_INDEX_NAME,
                                                       expireAfterSeconds=default_ttl)

    def _update_user_tokens_index(self, expire_hours):
        if expire_hours:
            new_ttl = 60 * 60 * expire_hours
            self._get_db_connection()[self.plugin_unique_name].command(
                'collMod', USERS_TOKENS_COLLECTION,
                index={'keyPattern': {USERS_TOKENS_COLLECTION_TTL_INDEX_NAME: 1},
                       'expireAfterSeconds': new_ttl})

    def __add_defaults(self):
        self._add_default_roles()
        no_access_role_id = self.get_default_external_role_id(self._roles_collection)
        config, schema = self._get_plugin_configs(IDENTITY_PROVIDERS_CONFIG, GUI_PLUGIN_NAME)
        saml_login = config['saml_login_settings']
        ldap_login = config['ldap_login_settings']
        update_external_login_config = False
        for external_service in [saml_login, ldap_login]:
            role_assignment_rules = external_service.get(ROLE_ASSIGNMENT_RULES, {})
            if not role_assignment_rules.get(DEFAULT_ROLE_ID):
                role_assignment_rules[DEFAULT_ROLE_ID] = no_access_role_id
                update_external_login_config = True
        if update_external_login_config:
            self.plugins.gui.configurable_configs[IDENTITY_PROVIDERS_CONFIG] = config

        current_user = self._users_collection.find_one({'user_name': 'admin'})
        if current_user is None:
            owner_role = self._roles_collection.find_one({
                'name': PREDEFINED_ROLE_ADMIN
            })
            # User doesn't exist, this must be the installation process
            default_user = self.DEFAULT_USER
            default_user['role_id'] = owner_role.get('_id')
            admin_result = self._users_collection.insert_one(default_user)
            self._add_personal_space(admin_result.inserted_id)
        alt_user = self._users_collection.find_one({'user_name': AXONIUS_USER_NAME})
        if alt_user is None:
            owner_role = self._roles_collection.find_one({
                'name': PREDEFINED_ROLE_OWNER
            })
            alternatice_user = self.ALTERNATIVE_USER
            alternatice_user['role_id'] = owner_role.get('_id')
            axonius_user_result = self._users_collection.insert_one(alternatice_user)
            self._add_personal_space(axonius_user_result.inserted_id)

        alt_user = self._users_collection.find_one({'user_name': AXONIUS_RO_USER_NAME})
        if alt_user is None:
            owner_ro_role = self._roles_collection.find_one({
                'name': PREDEFINED_ROLE_OWNER_RO
            })
            alternative_user_ro = self.ALTERNATIVE_RO_USER
            alternative_user_ro['role_id'] = owner_ro_role.get('_id')
            axonius_ro_user_result = self._users_collection.insert_one(alternative_user_ro)
            self._add_personal_space(axonius_ro_user_result.inserted_id)

        self.add_default_views(EntityType.Devices, 'default_views_devices.ini')
        self.add_default_views(EntityType.Users, 'default_views_users.ini')
        self.add_default_dashboard_charts('default_dashboard_charts.ini')
        if not self.system_collection.count_documents({'type': 'server'}):
            self.system_collection.insert_one({'type': 'server', 'server_name': 'localhost'})
        if not self.system_collection.count_documents({'type': 'maintenance'}):
            self.system_collection.insert_one({
                'type': 'maintenance', 'provision': True, 'analytics': True, 'troubleshooting': True
            })

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args,
                         requested_unique_plugin_name=GUI_PLUGIN_NAME,
                         supported_api_versions=SUPPORTED_API_VERSIONS,
                         **kwargs)
        self.__all_sessions = {}
        self.wsgi_app.config['SESSION_COOKIE_SECURE'] = True
        self.wsgi_app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
        self.wsgi_app.session_interface = CachedSessionInterface(self.__all_sessions)
        self.wsgi_app.kvsession_store = self.__all_sessions

        self._users_collection = self._get_collection(USERS_COLLECTION)
        self._roles_collection = self._get_collection(ROLES_COLLECTION)
        self._users_tokens_collection = self._get_collection(USERS_TOKENS_COLLECTION)
        self._users_preferences_collection = self._get_collection(USERS_PREFERENCES_COLLECTION)
        self._dashboard_spaces_collection = self._get_collection(DASHBOARD_SPACES_COLLECTION)

        self.reports_config_collection.create_index([('name', pymongo.HASHED)])

        self.cortex_root_dir = Path().cwd().parent
        self.upload_files_dir = Path(self.cortex_root_dir, 'uploaded_files')
        self.upload_files_list = {}
        self.latest_version = None
        if read_saas_input_params():
            self.ssm_client = SaasSecretsManager()
            self.saas_params = read_saas_input_params()
            self.tunnel_status = False
            self.tunnel_first_up = False
        elif os.environ.get(AXONIUS_SAAS_VAR_NAME):
            if Signup.SignupCollection in self._get_db_connection()[self.plugin_name].list_collection_names():
                company_name = self._get_collection(Signup.SignupCollection).find_one({}).get(Signup.CompanyField, '')
            else:
                company_name = ''
            with open(AXONIUS_SETTINGS_PATH / 'vpn_data' / 'user.ovpn', 'r') as fh:
                web_url = re.findall(r'remote\s(\d.*?)\s', fh.read())
            self.saas_params = {
                'AXONIUS_SAAS_NODE': 'True',
                'WEB_URL': f'https://{web_url}',
                'TUNNEL_URL': f'{web_url}:2212',
                'COMPANY_FOR_SIGNUP': company_name,
                'MACHINE_ENVIRONMENT': 'test' if os.environ.get('PROD') == 'false' else 'prod'
            }
            self.tunnel_status = False

        try:
            self._users_collection.create_index([('user_name', pymongo.ASCENDING),
                                                 ('source', pymongo.ASCENDING)], unique=True)
        except pymongo.errors.DuplicateKeyError as e:
            logger.critical(f'Error creating user_name and source unique index: {e}')

        self.__create_user_tokens_index()

        self.__add_defaults()

        # Start exec reports scheduler
        self.exec_report_locks = {}

        self._client_insertion_threadpool = LoggedThreadPoolExecutor(max_workers=10)  # Only for client insertion

        self._job_scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutorApscheduler(20)})
        current_exec_reports_setting = self._get_exec_report_settings(self.reports_config_collection)
        for current_exec_report_setting in current_exec_reports_setting:
            current_exec_report_setting['uuid'] = str(current_exec_report_setting['_id'])
            self._schedule_exec_report(current_exec_report_setting)
        self._job_scheduler.start()
        if self._maintenance_config.get('timeout'):
            next_run_time = self._maintenance_config['timeout']
            logger.info(f'Creating a job for stopping the maintenance access at {next_run_time}')
            self._job_scheduler.add_job(func=self._stop_temp_maintenance,
                                        trigger='date',
                                        next_run_time=next_run_time,
                                        name=TEMP_MAINTENANCE_THREAD_ID,
                                        id=TEMP_MAINTENANCE_THREAD_ID,
                                        max_instances=1)
        logger.info(self.metadata)
        self.encryption_key = self.load_encryption_key()
        self._set_first_time_use()
        self._trigger('clear_dashboard_cache', blocking=False)
        try:
            self.check_and_initialize_self_serve_instance()
        except Exception:
            logger.error('An exception happened while initializing self-server settings', exc_info=True)

        self._update_config_executor = ThreadPool(30)

        self._job_scheduler.add_job(func=self.get_latest_version,
                                    trigger=IntervalTrigger(minutes=30),
                                    next_run_time=datetime.now(),
                                    name='get_latest_version',
                                    id='get_latest_version',
                                    max_instances=1,
                                    coalesce=True)

    @property
    @cachetools.cached(cachetools.TTLCache(maxsize=1, ttl=300), lock=threading.Lock())
    def metadata(self):
        return self.load_metadata()

    def _add_default_roles(self):
        if self._roles_collection.find_one({'name': PREDEFINED_ROLE_OWNER}) is None:
            # Axonius Owner role doesn't exists - let's create it
            self._roles_collection.insert_one({
                'name': PREDEFINED_ROLE_OWNER,
                PREDEFINED_FIELD: True,
                'permissions': get_admin_permissions(),
                IS_AXONIUS_ROLE: True
            })
        if self._roles_collection.find_one({'name': PREDEFINED_ROLE_OWNER_RO}) is None:
            # Axonius Read Only role doesn't exists - let's create it
            axonius_ro_permissions = get_viewer_permissions()
            axonius_ro_permissions[PermissionCategory.Settings.value][PermissionAction.View.value] = True
            axonius_ro_permissions[PermissionCategory.Settings.value][PermissionAction.Update.value] = True
            self._roles_collection.insert_one({
                'name': PREDEFINED_ROLE_OWNER_RO,
                PREDEFINED_FIELD: True,
                'permissions': axonius_ro_permissions,
                IS_AXONIUS_ROLE: True
            })
        if self._roles_collection.find_one({'name': PREDEFINED_ROLE_ADMIN}) is None:
            # Admin role doesn't exists - let's create it
            self._roles_collection.insert_one({
                'name': PREDEFINED_ROLE_ADMIN,
                PREDEFINED_FIELD: True,
                'permissions': get_admin_permissions()

            })
        if self._roles_collection.find_one({'name': PREDEFINED_ROLE_VIEWER}) is None:
            # Viewer role doesn't exists - let's create it
            self._roles_collection.insert_one({
                'name': PREDEFINED_ROLE_VIEWER, PREDEFINED_FIELD: True, 'permissions': get_viewer_permissions()
            })
        if self._roles_collection.find_one({'name': PREDEFINED_ROLE_RESTRICTED}) is None:
            # Restricted role doesn't exists - let's create it. Everything restricted except the Dashboard.
            self._create_restricted_role()
        if self._roles_collection.find_one({'name': NO_ACCESS_ROLE}) is None:
            # No access role doesn't exists - let's create it. Everything restricted.
            self._roles_collection.insert_one({
                'name': NO_ACCESS_ROLE, PREDEFINED_FIELD: True,
                'permissions': serialize_db_permissions(get_permissions_structure(False))
            })

    def _delayed_initialization(self):
        self._init_all_dashboards()

    def check_and_initialize_self_serve_instance(self):
        if has_customer_login_happened():
            return
        # Two if statements so we wont make the request for nothing on every boot of non self-serve machine
        saas_params = read_saas_input_params()
        if not saas_params or 'AXONIUS_SAAS_NODE' not in saas_params or \
                ('AXONIUS_SAAS_NODE' in saas_params and saas_params['AXONIUS_SAAS_NODE'] == 'False'):
            return

        logger.info('Initializing self-serve settings')
        # Set trial to 30 days from now
        self.plugins.gui.configurable_configs.update_config(
            FeatureFlags.__name__,
            {
                FeatureFlagsNames.TrialEnd: (datetime.now() + timedelta(days=30)).isoformat()[:10].replace('-', '/')
            }
        )

        # Enable Tunnel feature flag automatically
        self.plugins.gui.configurable_configs.update_config(
            FeatureFlags.__name__,
            {
                FeatureFlagsNames.EnableSaaS: True
            }
        )

        # Set password policy

        self.plugins.core.configurable_configs.update_config(
            CORE_CONFIG_NAME,
            {
                f'{PASSWORD_SETTINGS}.enabled': True,
                f'{PASSWORD_SETTINGS}.{PASSWORD_LENGTH_SETTING}': 10,
                f'{PASSWORD_SETTINGS}.{PASSWORD_MIN_LOWERCASE}': 0,
                f'{PASSWORD_SETTINGS}.{PASSWORD_MIN_UPPERCASE}': 0,
                f'{PASSWORD_SETTINGS}.{PASSWORD_MIN_NUMBERS}': 0,
                f'{PASSWORD_SETTINGS}.{PASSWORD_MIN_SPECIAL_CHARS}': 0
            }
        )

        # Set password brute force protection
        self.plugins.core.configurable_configs.update_config(
            CORE_CONFIG_NAME,
            {
                f'{PASSWORD_BRUTE_FORCE_PROTECTION}.enabled': True,
                f'{PASSWORD_BRUTE_FORCE_PROTECTION}.{PASSWORD_PROTECTION_ALLOWED_RETRIES}': 20,
                f'{PASSWORD_BRUTE_FORCE_PROTECTION}.{PASSWORD_PROTECTION_LOCKOUT_MIN}': 5,
                f'{PASSWORD_BRUTE_FORCE_PROTECTION}.conditional': PASSWORD_PROTECTION_BY_IP
            }
        )

        # Set password reset link expiration to 1 week
        self.plugins.core.configurable_configs.update_config(
            CORE_CONFIG_NAME,
            {
                f'{RESET_PASSWORD_SETTINGS}.{RESET_PASSWORD_LINK_EXPIRATION}': 168
            }
        )

        # Automatic signup
        random_password = random_string(32)
        signup_data = {
            'companyName': saas_params.get('COMPANY_FOR_SIGNUP', 'Unknown company'),
            'newPassword': random_password,
            'confirmNewPassword': random_password,
            'contactEmail': saas_params.get('EMAIL_FOR_SIGNUP', 'unknown@email.com'),
            'userName': 'admin'
        }
        self._process_signup(manual_signup=signup_data)

        # Generate reset password link and send it to AWS
        admin_user_id = self._users_collection.find_one({'user_name': 'admin'}, projection=['_id'])['_id']
        reset_link = self.generate_user_reset_password_link(manual_user_id=str(admin_user_id))
        self.ssm_client.store_admin_password_reset_link(reset_link.replace('localhost', saas_params.get('WEB_URL')))

        # Add admin user for testing
        if saas_params.get('MACHINE_ENVIRONMENT', 'prod') == 'Test':
            self._create_user_if_doesnt_exist(
                username=DEFAULT_AWS_TEST_USER,
                first_name='Test',
                last_name='Test',
                email='test_axonius@axonius.com',
                picname=None,
                source='internal',
                password=DEFAULT_AWS_TEST_PASSWORD,
                role_id=self._roles_collection.find_one({'name': 'Admin'}, projection=['_id'])['_id']
            )
        logger.info('Done configuring self-serve settings')

    @staticmethod
    def get_stack_name(params):
        return params.get('STACK_NAME')

    @staticmethod
    def get_params_key_id(params):
        return params.get('PARAMS_KEY_ARN').split('/')[1]

    def add_default_dashboard_charts(self, default_dashboard_charts_ini_path):
        try:
            default_dashboards = []
            config = configparser.ConfigParser()
            config.read(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                     f'configs/{default_dashboard_charts_ini_path}')))
            default_space = self._dashboard_spaces_collection.find_one({
                'type': 'default'
            })
            if not default_space:
                logger.error('This Axonius is missing the default Dashboard')
                return

            for name, data in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    if self._dashboard_collection.find_one({'name': name}):
                        logger.info(f'dashboard with {name} already exists, not adding')
                        continue

                    dashboard_id = self._insert_dashboard_chart(dashboard_name=name,
                                                                dashboard_metric=data['metric'],
                                                                dashboard_view=data['view'],
                                                                dashboard_data=json.loads(data['config']),
                                                                hide_empty=bool(data.get('hide_empty', 0)),
                                                                space_id=default_space['_id'])
                    default_dashboards.append(str(dashboard_id))
                except Exception as e:
                    logger.exception(f'Error adding default dashboard chart {name}. Reason: {repr(e)}')
            if not default_space.get('panels_order'):
                # if panels_order attribute does not exist on space add it
                self._dashboard_spaces_collection.update_one({
                    'type': 'default',
                    '_id': default_space['_id']
                }, {
                    '$set': {
                        'panels_order': default_dashboards
                    }
                })

        except Exception as e:
            logger.exception(f'Error adding default dashboard chart. Reason: {repr(e)}')

    def add_default_views(self, entity_type: EntityType, default_views_ini_path):
        """
        Adds default views.
        :param entity_type: EntityType
        :param default_views_ini_path: the file path with the views
        :return:
        """
        # Load default views and save them to the DB
        try:
            config = configparser.ConfigParser()
            config.read(os.path.abspath(os.path.join(os.path.dirname(__file__), f'configs/{default_views_ini_path}')))

            # Save default views
            for name, data in config.items():
                if name == 'DEFAULT':
                    # ConfigParser always has a fake DEFAULT key, skip it
                    continue
                try:
                    query_view = data['view']
                    if data.get('should_replace_query_names', False):
                        logger.debug(f'replacing query names with ids for: {name}')
                        query_view = self._replace_predefined_query_references(
                            self.common.data.entity_views_collection[entity_type], data['view'])
                    self._insert_view(
                        self.common.data.entity_views_collection[entity_type],
                        name,
                        json.loads(query_view),
                        data.get('description', ''),
                        json.loads(data.get('tags', '[]')),
                        data.get('type', 'saved'))
                except Exception:
                    logger.exception(f'Error adding default view {name}')
        except Exception:
            logger.exception(f'Error adding default views')

    def compare_versions(self) -> bool:
        """
        check if latest version release is newer than installed version. if so, update metadata
        :return: True if there is a new release
        """
        installed_version = None
        try:
            if INSTALLED_VERISON_KEY not in self.metadata.keys() or not self.metadata[INSTALLED_VERISON_KEY] \
                    or not self.latest_version:
                return False
            installed_version = self.metadata[INSTALLED_VERISON_KEY].replace('_', '.')
            latest_version = self.latest_version.replace('_', '.')
            # remove patch version number
            splitted_installed_version = '.'.join(installed_version.split('.')[:2])
            splitted_latest_version = '.'.join(latest_version.split('.')[:2])

            if StrictVersion(splitted_latest_version) > StrictVersion(splitted_installed_version):
                self.metadata['Latest Available Version'] = self.latest_version
                return True
        except Exception:
            logger.exception(f'Error comparing versions. installed version: {installed_version}, '
                             f'available version: {self.latest_version}')
        return False

    @staticmethod
    def _replace_predefined_query_references(views_collection, query_view: str):
        matches = re.findall(PREDEFINED_SAVED_QUERY_REF_REGEX, query_view)
        for match in matches:
            existing_view = views_collection.find_one({
                'name': {
                    '$regex': match,
                    '$options': 'i'
                },
                PREDEFINED_FIELD: True,
                UPDATED_BY_FIELD: '*'
            })
            if not existing_view:
                logger.error(f'Unable to find {match} in views.')
                continue
            found_query_id = str(existing_view['_id'])
            logger.debug(f'replacing predefined reference {match} with {found_query_id}')
            query_view = query_view.replace(f'<QUERY_NAME={match}>', found_query_id)
        return query_view

    def get_latest_version(self):
        """
        Get latest Axonius release version
        :return:
        """
        try:
            # Use global gui proxies
            proxies = {
                'https': to_proxy_string(self._proxy_settings)
            }
            res = requests.get(LATEST_VERSION_URL, timeout=10, proxies=proxies,
                               verify=self._proxy_settings[PROXY_VERIFY])

            if res.status_code != 200:
                logger.error(f'Error getting axonius latest version, status code: {res.status_code}')
                return
            self.latest_version = res.text
            self.compare_versions()
        except Exception:
            logger.error(f'Error getting axonius latest version', exc_info=True)

    def load_metadata(self):
        try:
            config, schema = self._get_plugin_configs(FEATURE_FLAGS_CONFIG, GUI_PLUGIN_NAME)
            metadata_bytes = ''
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH, 'r', encoding='UTF-8') as metadata_file:
                    metadata_bytes = metadata_file.read().strip().replace('\\', '\\\\')
                    metadata_json = json.loads(metadata_bytes)
                    if 'Commit Hash' in metadata_json:
                        del metadata_json['Commit Hash']
                    if 'Commit Date' in metadata_json:
                        del metadata_json['Commit Date']
                    metadata_json['Customer ID'] = self.node_id
                    metadata_json['Installed Version'] = metadata_json.pop('Version', None)
                    if config.get(FeatureFlagsNames.ExpiryDate, ''):
                        metadata_json['Contract Expiry Date'] = config.get(FeatureFlagsNames.ExpiryDate)
                    return metadata_json
        except Exception:
            logger.exception(f'Bad __build_metadata file {metadata_bytes}')
            return ''

    @staticmethod
    def load_encryption_key():
        try:
            if os.path.exists(ENCRYPTION_KEY_PATH):
                with open(ENCRYPTION_KEY_PATH, 'r') as encryption_key_file:
                    encryption_key_bytes = encryption_key_file.read().strip()
                    return str(encryption_key_bytes)
        except Exception:
            logger.exception(f'Bad __encryption_key file {encryption_key_bytes}')
            return ''

    def _set_first_time_use(self):
        """
        Check the clients db of each registered adapter to determine if there is any connected adapter.
        We regard no connected adapters as a fresh system, that should offer user a tutorial.
        Answer is saved in a private member that is read by the frontend via a designated endpoint.

        """
        plugins_available = self.get_available_plugins_from_core()
        self._is_system_first_use = True
        db_connection = self._get_db_connection()
        adapters_from_db = db_connection['core']['configs'].find({
            'plugin_type': {
                '$in': [
                    'Adapter', 'ScannerAdapter'
                ]
            }
        }).sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)])
        for adapter in adapters_from_db:
            if adapter[PLUGIN_UNIQUE_NAME] in plugins_available and db_connection[adapter[PLUGIN_UNIQUE_NAME]][
                    'clients'].count_documents({}, limit=1):
                self._is_system_first_use = False

    @staticmethod
    def store_proxy_data(proxy_settings):
        try:

            # This string is used by chef!
            proxy_string = to_proxy_string(proxy_settings)
            verify = proxy_settings[PROXY_VERIFY]

            proxy_json = {
                'creds': proxy_string,
                'verify': verify
            }

            proxy_data = json.dumps(proxy_json)
            PROXY_DATA_PATH.write_text(proxy_data)  # saving proxy data to a folder readable from outside
            logger.info(f'updating proxy settings: {proxy_settings}')

        except Exception:
            logger.exception(f'Failed to set proxy settings from gui {proxy_settings}')

    def dump_metrics(self):
        try:
            self.dump_connection_status()

            # Uncached because the values here are important for metrics
            adapter_devices = adapter_data.call_uncached(EntityType.Devices)
            adapter_users = adapter_data.call_uncached(EntityType.Users)

            axonius_roles = self._roles_collection.find({
                IS_AXONIUS_ROLE: True
            }, {'_id': 1})
            log_metric(logger, SystemMetric.GUI_USERS,
                       self._users_collection.count_documents(filter_archived({
                           'role_id': {
                               '$nin': [role['_id'] for role in axonius_roles]
                           }
                       })))
            log_metric(logger, SystemMetric.DEVICES_SEEN, adapter_devices['seen'])
            log_metric(logger, SystemMetric.DEVICES_UNIQUE, adapter_devices['unique'])

            log_metric(logger, SystemMetric.USERS_SEEN, adapter_users['seen'])
            log_metric(logger, SystemMetric.USERS_UNIQUE, adapter_users['unique'])

            enforcements = self._get_enforcements(limit=0,
                                                  mongo_filter={},
                                                  mongo_sort={},
                                                  skip=0)

            log_metric(logger, SystemMetric.ENFORCEMENTS_COUNT, len(enforcements))
            for enforcement in enforcements:
                enforcement.pop('_id', None)
                log_metric(logger, SystemMetric.ENFORCEMENT_RAW, dumps(enforcement))

            for action in self.enforcements_saved_actions_collection.find({}, projection={'_id': False}):
                log_metric(logger, SystemMetric.EC_ACTION_RAW, dumps(action))

            for view_type, view_collection in self.common.data.entity_views_collection.items():
                log_metric(logger,
                           SystemMetric.STORED_VIEWS_COUNT,
                           metric_value=view_collection.count_documents(filter_archived({
                               'query_type': 'saved',
                               '$or': [
                                   {
                                       PREDEFINED_FIELD: False
                                   },
                                   {
                                       PREDEFINED_FIELD: {
                                           '$exists': False
                                       }
                                   }
                               ]
                           })),
                           view_type=str(view_type))
                for view in view_collection.find({}, projection={'_id': False}):
                    log_metric(logger, SystemMetric.STORED_VIEW_RAW, metric_value=dumps(view),
                               view_type=str(view_type))

            plugins_by_plugin_name = {x[PLUGIN_NAME]
                                      for x
                                      in self.get_available_plugins_from_core().values()}

            def dump_per_adapter(mapping, subtype):
                counters = mapping['counters']
                plugins_left = set(plugins_by_plugin_name)
                for counter in counters:
                    log_metric(logger, f'adapter.{subtype}.{counter["name"]}.entities', counter['value'])
                    log_metric(logger, f'adapter.{subtype}.{counter["name"]}.entities.meta', counter['meta'])
                    plugins_left -= {counter['name']}
                for name in plugins_left:
                    log_metric(logger, f'adapter.{subtype}.{name}.entities', 0)
                    log_metric(logger, f'adapter.{subtype}.{name}.entities.meta', 0)

            dump_per_adapter(adapter_devices, 'devices')
            dump_per_adapter(adapter_users, 'users')
        except Exception:
            logger.exception('Failed to dump metrics')

    def dump_connection_status(self):
        try:
            adapters = self._adapters()
            for adapter_name, value in adapters.items():
                for adapter in value:
                    unique_plugin_name = adapter['unique_plugin_name']
                    node_name = adapter['node_name']
                    clients = adapter['clients']
                    for client in clients:
                        client.pop('client_config', None)
                        client.pop('last_fetch_time', None)
                        client.pop('date_fetched', None)
                        client.pop('error', None)
                        log_metric(logger=logger,
                                   metric_name=SystemMetric.ADAPTER_CONNECTION_INFO,
                                   metric_value=str(client),
                                   adapter_name=adapter_name,
                                   unique_plugin_name=unique_plugin_name,
                                   node_name=node_name)
        except Exception:
            logger.exception(f'Failed to report per adapter connection status')

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.PostCorrelation

    @property
    def system_collection(self):
        return self._get_collection(GUI_SYSTEM_CONFIG_COLLECTION)

    @property
    def reports_config_collection(self):
        return self._get_collection('reports_config')

    @property
    def exec_report_collection(self):
        return self._get_collection('exec_reports_settings')

    @property
    def _nodes_metadata_collection(self):
        return self._get_collection(db_name=CORE_UNIQUE_NAME, collection_name='nodes_metadata')

    @property
    def _dashboard_collection(self):
        return self._get_collection(DASHBOARD_COLLECTION)

    def get_plugin_unique_name(self, plugin_name):
        return self.get_plugin_by_name(plugin_name)[PLUGIN_UNIQUE_NAME]

    def _on_config_update(self, config):
        self._system_settings = config[SYSTEM_SETTINGS]
        self._mutual_tls_settings = config['mutual_tls_settings']
        mutual_tls_is_mandatory = self._mutual_tls_settings.get('mandatory')
        ca_certificate = self._grab_file_contents(self._mutual_tls_settings.get('ca_certificate'))

        if self._mutual_tls_settings.get('enabled') and mutual_tls_is_mandatory:
            # Enable Mutual TLS.
            # Note that we have checked before (plugin_configs) that the issuer is indeed part of this cert
            # as input validation. So input validation is not needed here.
            try:

                current_ca_cert = None
                if os.path.exists(MUTUAL_TLS_CA_PATH):
                    with open(MUTUAL_TLS_CA_PATH, 'rb') as mtls_file:
                        current_ca_cert = mtls_file.read()

                if not current_ca_cert or current_ca_cert != ca_certificate:
                    logger.info(f'Writing mutual tls settings')
                    with open(MUTUAL_TLS_CA_PATH, 'wb') as mtls_file:
                        mtls_file.write(ca_certificate)

                    with open(MUTUAL_TLS_CONFIG_FILE, 'wt') as mtls_config_file:
                        mtls_config_file.write(
                            f'ssl_verify_client on;\r\n'
                            f'ssl_verify_depth 10;\r\n'
                            f'ssl_client_certificate {MUTUAL_TLS_CA_PATH};\r\n'
                        )
                    # Restart Openresty (NGINX)
                    subprocess.check_call(['openresty', '-s', 'reload'])
                    logger.info(f'Successfuly loaded new mutual TLS settings')
            except Exception:
                logger.critical(f'Can not get mutual tls ca certificate, system is not protected', exc_info=True)
        else:
            # Disable mandatory Mutual TLS
            mutual_tls_state = f'optional_no_ca' if self._mutual_tls_settings.get('enabled') else 'off'
            try:
                if os.path.exists(MUTUAL_TLS_CA_PATH) or ca_certificate:
                    logger.info(f'Deleting mutual tls settings')
                    with open(MUTUAL_TLS_CONFIG_FILE, 'wt') as mtls_config_file:
                        mtls_config_file.write(f'ssl_verify_client {mutual_tls_state};')
                    # Restart Openresty (NGINX)
                    subprocess.check_call(['openresty', '-s', 'reload'])
                    try:
                        os.unlink(MUTUAL_TLS_CA_PATH)
                    except FileNotFoundError:
                        # Already deleted is fine in case ca_certificate has value
                        pass
                    logger.info(f'Successfuly loaded new mutual TLS settings: {mutual_tls_state}')
            except Exception:
                logger.exception(f'Can not delete mutual tls settings')

    def _global_config_updated(self):
        self.store_proxy_data(self._proxy_settings)

    @property
    def _maintenance_config(self):
        return self.system_collection.find_one({
            'type': 'maintenance'
        })

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'items': [
                        {
                            'name': 'refreshRate',
                            'title': 'Auto-refresh rate (seconds)',
                            'type': 'number'
                        },
                        {
                            'name': 'defaultNumOfEntitiesPerPage',
                            'title': 'Default number of query results displayed per page',
                            'type': 'string',
                            'enum': [20, 50, 100]
                        },
                        {
                            'name': 'defaultSort',
                            'title': 'When no column sort is applied, sort by count of adapters',
                            'type': 'bool'
                        },
                        {
                            'name': 'autoQuery',
                            'title': 'Perform a query every keypress',
                            'type': 'bool'
                        },
                        {
                            'name': 'exactSearch',
                            'title': 'Use exact match for assets search',
                            'type': 'bool',
                        },
                        {
                            'name': 'requireConnectionLabel',
                            'title': 'Require Connection Label on each adapter connection',
                            'type': 'bool',
                        },
                        {
                            'name': 'defaultColumnLimit',
                            'title': 'Number of values displayed in each column',
                            'type': 'string',
                            'enum': [1, 2]
                        },
                        {
                            'name': 'cell_joiner',
                            'title': 'Export CSV delimiter to use for multi-value fields',
                            'type': 'string'
                        },
                        {
                            'name': 'datetime_format',
                            'title': 'Date format',
                            'type': 'string',
                            'enum': ['YYYY-MM-DD', 'DD-MM-YYYY', 'MM-DD-YYYY']
                        },
                        {
                            'name': 'timeout_settings',
                            'title': 'Timeout Settings',
                            'items': [
                                {
                                    'name': 'enabled',
                                    'title': 'Enable session timeout',
                                    'type': 'bool'
                                },
                                {
                                    'name': 'disable_remember_me',
                                    'title': 'Disable \'Remember me\'',
                                    'type': 'bool',
                                    'default': False
                                },
                                {
                                    'name': 'timeout',
                                    'title': 'Session idle timeout (minutes)',
                                    'type': 'number',
                                    'default': 1440
                                }
                            ],
                            'required': ['enabled', 'timeout', 'disable_remember_me'],
                            'type': 'array'
                        },
                        {
                            'name': 'cache_settings',
                            'title': 'Cache Settings',
                            'items': [
                                {
                                    'name': 'enabled',
                                    'title': 'Enable caching on recently used queries',
                                    'type': 'bool'
                                },
                                {
                                    'name': 'ttl',
                                    'title': 'Cache Time-to-Live (TTL) in minutes',
                                    'type': 'number',
                                    'default': 60,
                                    'max': 20160
                                }
                            ],
                            'required': ['enabled', 'ttl'],
                            'type': 'array'
                        }
                    ],
                    'required': ['refreshRate', 'defaultNumOfEntitiesPerPage',
                                 'defaultSort', 'autoQuery', 'exactSearch', 'requireConnectionLabel',
                                 'defaultColumnLimit', 'datetime_format', 'cache_settings'],
                    'name': SYSTEM_SETTINGS,
                    'title': 'System Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Enable mutual TLS',
                            'type': 'bool'
                        },
                        {
                            'name': 'mandatory',
                            'title': 'Enforce client certificate validation',
                            'type': 'bool'
                        },
                        {
                            'name': 'ca_certificate',
                            'title': 'CA certificate',
                            'description': 'A pem encoded certificate to authenticate users',
                            'type': 'file'
                        }
                    ],
                    'required': ['enabled', 'ca_certificate', 'mandatory'],
                    'name': 'mutual_tls_settings',
                    'hidden': True,
                    'title': 'Mutual TLS Settings',
                    'type': 'array'
                },
            ],
            'type': 'array',
            'pretty_name': 'GUI Settings'
        }

    @classmethod
    def _db_config_default(cls):
        # pylint: disable=protected-access

        return {
            SYSTEM_SETTINGS: {
                'refreshRate': 60,
                'cell_joiner': None,
                'defaultNumOfEntitiesPerPage': 20,
                'timeout_settings': {
                    'disable_remember_me': False,
                    'enabled': False,
                    'timeout': 1440
                },
                'cache_settings': {
                    'enabled': False,
                    'ttl': 60
                },
                'datetime_format': 'YYYY-MM-DD',
                'defaultSort': True,
                'autoQuery': True,
                'exactSearch': True,
                'requireConnectionLabel': False,
                'defaultColumnLimit': 2
            },
            'mutual_tls_settings': {
                'enabled': False,
                'mandatory': False,
                'ca_certificate': None
            }
        }

    def _get_entity_count(self, entity, mongo_filter, history, quick):
        col, is_date_filter_required = self.get_appropriate_view(history, entity)
        return str(get_entities_count(
            mongo_filter,
            col,
            history_date=history,
            quick=quick,
            is_date_filter_required=is_date_filter_required))

    def _get_entity_count_cached(self, entity, mongo_filter, history,
                                 quick, is_cache_enabled, use_cache_entry, cache_ttl):
        col, is_date_filter_required = self.get_appropriate_view(history, entity)
        # pylint: disable=unexpected-keyword-arg
        count, _ = get_entities_count_cached(
            col,
            entity,
            mongo_filter,
            history_date=history,
            quick=quick,
            is_date_filter_required=is_date_filter_required,
            is_cache_enabled=is_cache_enabled,
            use_cache_entry=use_cache_entry,
            cache_ttl=cache_ttl)
        return str(count)

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name == 'clear_dashboard_cache':
            self._clear_dashboard_cache(clear_slow=post_json is not None and post_json.get('clear_slow') is True)

            # Don't clean too often!
            time.sleep(5)
            return ''

        elif job_name == 'check_tunnel_status':
            return self.check_tunnel_status(internal_use=True)

        elif job_name == 'tunnel_is_down':
            self._tunnel_is_down()
            return ''

        elif job_name == 'tunnel_is_up':
            self._tunnel_is_up()
            return ''

        elif job_name == 'execute':
            # GUI is a post correlation plugin, thus this is called near the end of the cycle
            self._trigger('clear_dashboard_cache', blocking=False)
            self.dump_metrics()
            return self.generate_new_reports_offline()
        raise RuntimeError(f'GUI was called with a wrong job name {job_name}')

    def _invalidate_sessions(self, user_ids: List[str] = None):
        """
        Invalidate all sessions for this user except the current one
        """
        user_ids_set = set(user_ids) if user_ids else {}
        for k, v in self.__all_sessions.items():
            # Pylint is angry because it thinks session is a dict, which is true for HOT=True
            # pylint: disable=no-member
            if k == session.sid:
                continue
            # pylint: enable=no-member
            d = v.get('d')
            if not d:
                continue
            user = d.get('user')
            if user and (not user_ids or str(d['user'].get('_id')) in user_ids_set):
                d['user'] = None

    def _invalidate_sessions_for_role(self, role_id: str = None):
        """
        Invalidate all sessions for all the users with this role
        """
        users = self._users_collection.find({'role_id': ObjectId(role_id)})
        user_ids = {user.get('_id') for user in users}
        for k, v in self.__all_sessions.items():
            d = v.get('d')
            if not d:
                continue
            user = d.get('user')
            if user and (not role_id or d['user'].get('_id') in user_ids):
                d['user'] = None

    @staticmethod
    def set_session_user(user):
        session['user'] = user

    @property
    def get_user(self):
        return session.get('user', {}) or {}

    def is_admin_user(self):
        return is_role_admin(self.get_user)

    def is_api_user(self):
        return self.get_user.get(IS_API_USER)

    def is_axonius_user(self):
        return is_axonius_role(self.get_user)

    def get_user_permissions(self):
        permissions = session.get('user', {}).get('permissions', {})
        if not permissions and g.api_user_permissions:
            permissions = g.api_user_permissions
        return permissions

    def get_user_role_id(self) -> ObjectId:
        return session.get('user', {}).get('role_id', '')

    @property
    def saml_settings_file_path(self):
        return SAML_SETTINGS_FILE_PATH

    @rev_cached(ttl=3600)
    def _get_environment_name(self):
        instance = self._nodes_metadata_collection.find_one({NODE_USE_AS_ENV_NAME: True})
        return instance.get(NODE_NAME, '') if instance is not None else ''

    def log_activity_user(self, category: AuditCategory, action: AuditAction, params: Dict[str, str] = None):
        self.log_activity_user_default(category.value, action.value, params)

    def log_activity_user_default(self, category: str, action: str, params: Dict[str, str] = None):
        if self.is_axonius_user():
            return
        audit_type = AuditType.User
        if self.is_api_user():
            audit_type = AuditType.Api
        super().log_activity_default(category, action, params, audit_type, get_connected_user_id())
