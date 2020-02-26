import json
import logging
import os
import secrets
import subprocess
import time
import configparser

import pymongo
from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from flask import (session)
# pylint: disable=import-error
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.clients.ldap.ldap_group_cache import set_ldap_groups_cache, get_ldap_groups_cache_ttl
from axonius.consts.gui_consts import (ENCRYPTION_KEY_PATH,
                                       PREDEFINED_ROLE_RESTRICTED,
                                       ROLES_COLLECTION,
                                       TEMP_MAINTENANCE_THREAD_ID,
                                       USERS_COLLECTION,
                                       USERS_CONFIG_COLLECTION,
                                       DASHBOARD_COLLECTION, DASHBOARD_SPACES_COLLECTION,
                                       PROXY_DATA_PATH)
from axonius.consts.metric_consts import SystemMetric
from axonius.consts.plugin_consts import (AXONIUS_USER_NAME,
                                          GUI_PLUGIN_NAME,
                                          GUI_SYSTEM_CONFIG_COLLECTION,
                                          METADATA_PATH, PLUGIN_NAME, PLUGIN_UNIQUE_NAME, SYSTEM_SETTINGS, PROXY_VERIFY)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.devices.device_adapter import DeviceAdapter
from axonius.logging.metric_helper import log_metric
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import (RunIdentifier,
                                        Triggerable)
from axonius.plugin_base import EntityType, PluginBase
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.types.ssl_state import (COMMON_SSL_CONFIG_SCHEMA,
                                     COMMON_SSL_CONFIG_SCHEMA_DEFAULTS)
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.gui_helpers import (deserialize_db_permissions, get_entities_count)
from axonius.utils.proxy_utils import to_proxy_string
from axonius.utils.ssl import MUTUAL_TLS_CA_PATH, \
    MUTUAL_TLS_CONFIG_FILE
from gui.api import APIMixin
from gui.cached_session import CachedSessionInterface
from gui.feature_flags import FeatureFlags
from gui.logic.dashboard_data import (adapter_data)
from gui.routes.app_routes import AppRoutes

# pylint: disable=invalid-name,too-many-instance-attributes,inconsistent-return-statements,too-many-statements,no-else-return,no-self-use

logger = logging.getLogger(f'axonius.{__name__}')

SAML_SETTINGS_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config', 'saml_settings.json'))


if os.environ.get('HOT') == 'true':
    session = None


class GuiService(Triggerable, FeatureFlags, PluginBase, Configurable, APIMixin, AppRoutes):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    class MyUserAdapter(UserAdapter):
        pass

    DEFAULT_AVATAR_PIC = '/src/assets/images/users/avatar.png'
    ALT_AVATAR_PIC = '/src/assets/images/users/alt_avatar.png'
    DEFAULT_USER = {'user_name': 'admin',
                    'password':
                        '$2b$12$SjT4qshlg.uUpsgE3vHwp.7A0UtkGEoWfUR0wFet3WZuXTnMgOCIK',
                    'first_name': 'administrator', 'last_name': '',
                    'pic_name': DEFAULT_AVATAR_PIC,
                    'permissions': {},
                    'admin': True,
                    'source': 'internal',
                    'api_key': secrets.token_urlsafe(),
                    'api_secret': secrets.token_urlsafe()
                    }

    ALTERNATIVE_USER = {'user_name': AXONIUS_USER_NAME,
                        'password':
                            '$2b$12$HQTyeTlepuCDC.5ZJ0TFo.U9ZUBARAEFU5pjhcnY.GfWaQWydcn8G',
                        'first_name': 'axonius', 'last_name': '',
                        'pic_name': ALT_AVATAR_PIC,
                        'permissions': {},
                        'admin': True,
                        'source': 'internal',
                        'api_key': secrets.token_urlsafe(),
                        'api_secret': secrets.token_urlsafe()
                        }

    def __add_defaults(self):
        self._add_default_roles()
        if self._users_config_collection.find_one({}) is None:
            self._users_config_collection.insert_one({
                'external_default_role': PREDEFINED_ROLE_RESTRICTED
            })

        current_user = self._users_collection.find_one({'user_name': 'admin'})
        if current_user is None:
            # User doesn't exist, this must be the installation process
            self._users_collection.update({'user_name': 'admin'}, self.DEFAULT_USER, upsert=True)

        alt_user = self._users_collection.find_one({'user_name': AXONIUS_USER_NAME})
        if alt_user is None:
            self._users_collection.update({'user_name': AXONIUS_USER_NAME}, self.ALTERNATIVE_USER, upsert=True)

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
        super().__init__(get_local_config_file(__file__), *args, requested_unique_plugin_name=GUI_PLUGIN_NAME, **kwargs)
        self.__all_sessions = {}
        self.wsgi_app.config['SESSION_COOKIE_SECURE'] = True
        self.wsgi_app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
        self.wsgi_app.session_interface = CachedSessionInterface(self.__all_sessions)

        self._users_collection = self._get_collection(USERS_COLLECTION)
        self._roles_collection = self._get_collection(ROLES_COLLECTION)
        self._users_config_collection = self._get_collection(USERS_CONFIG_COLLECTION)
        self._dashboard_collection = self._get_collection(DASHBOARD_COLLECTION)
        self._dashboard_spaces_collection = self._get_collection(DASHBOARD_SPACES_COLLECTION)

        self.reports_config_collection.create_index([('name', pymongo.HASHED)])

        try:
            self._users_collection.create_index([('user_name', pymongo.ASCENDING),
                                                 ('source', pymongo.ASCENDING)], unique=True)
        except pymongo.errors.DuplicateKeyError as e:
            logger.critical(f'Error creating user_name and source unique index: {e}')

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

        self.metadata = self.load_metadata()
        self.encryption_key = self.load_encryption_key()
        self._set_first_time_use()

        self._trigger('clear_dashboard_cache', blocking=False)

        if os.environ.get('HOT') == 'true':
            # pylint: disable=W0603
            global session
            user_db = self._users_collection.find_one({'user_name': 'admin'})
            user_db['permissions'] = deserialize_db_permissions(user_db['permissions'])
            session = {'user': user_db}

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
                    self._insert_view(
                        self.gui_dbs.entity_query_views_db_map[entity_type],
                        name,
                        json.loads(data['view']),
                        data.get('description', ''),
                        json.loads(data.get('tags', '[]')))
                except Exception:
                    logger.exception(f'Error adding default view {name}')
        except Exception:
            logger.exception(f'Error adding default views')

    @staticmethod
    def _is_hidden_user():
        return (session.get('user') or {}).get('user_name') == AXONIUS_USER_NAME

    def _delayed_initialization(self):
        self._init_all_dashboards()

    @staticmethod
    def load_metadata():
        try:
            metadata_bytes = ''
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH, 'r', encoding='UTF-8') as metadata_file:
                    metadata_bytes = metadata_file.read().strip().replace('\\', '\\\\')
                    return json.loads(metadata_bytes)
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
            # Uncached because the values here are important for metrics
            adapter_devices = adapter_data.call_uncached(EntityType.Devices)
            adapter_users = adapter_data.call_uncached(EntityType.Users)

            log_metric(logger, SystemMetric.GUI_USERS, self._users_collection.count_documents({}))
            log_metric(logger, SystemMetric.DEVICES_SEEN, adapter_devices['seen'])
            log_metric(logger, SystemMetric.DEVICES_UNIQUE, adapter_devices['unique'])

            log_metric(logger, SystemMetric.USERS_SEEN, adapter_users['seen'])
            log_metric(logger, SystemMetric.USERS_UNIQUE, adapter_users['unique'])

            enforcements = self.get_enforcements(limit=0,
                                                 mongo_filter={},
                                                 mongo_sort={},
                                                 skip=0)
            for enforcement in enforcements:
                log_metric(logger, SystemMetric.ENFORCEMENT_RAW, str(enforcement))

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

    def get_plugin_unique_name(self, plugin_name):
        return self.get_plugin_by_name(plugin_name)[PLUGIN_UNIQUE_NAME]

    def _on_config_update(self, config):
        self._okta = config['okta_login_settings']
        self._saml_login = config['saml_login_settings']
        self._ldap_login = config['ldap_login_settings']
        self._system_settings = config[SYSTEM_SETTINGS]
        self._mutual_tls_settings = config['mutual_tls_settings']
        mutual_tls_is_mandatory = self._mutual_tls_settings.get('mandatory')

        if self._mutual_tls_settings.get('enabled') and mutual_tls_is_mandatory:
            # Enable Mutual TLS.
            # Note that we have checked before (plugin_configs) that the issuer is indeed part of this cert
            # as input validation. So input validation is not needed here.
            try:
                ca_certificate = self._grab_file_contents(self._mutual_tls_settings.get('ca_certificate'))

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
                if os.path.exists(MUTUAL_TLS_CA_PATH):
                    logger.info(f'Deleting mutual tls settings')
                    with open(MUTUAL_TLS_CONFIG_FILE, 'wt') as mtls_config_file:
                        mtls_config_file.write(f'ssl_verify_client {mutual_tls_state};')
                    # Restart Openresty (NGINX)
                    subprocess.check_call(['openresty', '-s', 'reload'])
                    os.unlink(MUTUAL_TLS_CA_PATH)
                    logger.info(f'Successfuly loaded new mutual TLS settings: {mutual_tls_state}')
            except Exception:
                logger.exception(f'Can not delete mutual tls settings')

        metadata_url = self._saml_login.get('metadata_url')
        if metadata_url:
            try:
                logger.info(f'Requesting metadata url for SAML Auth')
                self._saml_login['idp_data_from_metadata'] = \
                    OneLogin_Saml2_IdPMetadataParser.parse_remote(metadata_url)
            except Exception:
                logger.exception(f'SAML Configuration change: Metadata parsing error')
                self.create_notification(
                    'SAML config change failed',
                    content='The metadata URL provided is invalid.',
                    severity_type='error'
                )

        try:
            new_ttl = self._ldap_login.get('cache_time_in_hours')
            new_ttl = new_ttl if new_ttl is not None else 1

            if (get_ldap_groups_cache_ttl() / 3600) != new_ttl:
                logger.info(f'Setting a new cache with ttl of {new_ttl} hours')
                set_ldap_groups_cache(new_ttl * 3600)
        except Exception:
            logger.exception(f'Failed - could not add LDAP groups cached')

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
                            'name': 'singleAdapter',
                            'title': 'Use single adapter view',
                            'type': 'bool'
                        },
                        {
                            'name': 'multiLine',
                            'title': 'Use table multi line view',
                            'type': 'bool'
                        },
                        {
                            'name': 'defaultSort',
                            'title': 'Sort by number of adapters in default view',
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
                            'name': 'defaultColumnLimit',
                            'title': 'Number of values displayed in each column',
                            'type': 'string',
                            'enum': [1, 2]
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
                            'name': 'percentageThresholds',
                            'title': 'Percentage Fields Severity Scopes',
                            'type': 'array',
                            'items': [
                                {
                                    'name': 'error',
                                    'title': 'Poor under:',
                                    'type': 'integer'
                                },
                                {
                                    'name': 'warning',
                                    'title': 'Average under:',
                                    'type': 'integer'
                                },
                                {
                                    'name': 'success',
                                    'title': 'Good under:',
                                    'type': 'integer'
                                }
                            ],
                            'required': ['error', 'warning', 'success']
                        }
                    ],
                    'required': ['refreshRate', 'defaultNumOfEntitiesPerPage', 'singleAdapter', 'multiLine',
                                 'defaultSort', 'autoQuery', 'exactSearch', 'defaultColumnLimit'],
                    'name': SYSTEM_SETTINGS,
                    'title': 'System Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Allow Okta logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'client_id',
                            'title': 'Okta application client ID',
                            'type': 'string'
                        },
                        {
                            'name': 'client_secret',
                            'title': 'Okta application client secret',
                            'type': 'string',
                            'format': 'password'
                        },
                        {
                            'name': 'url',
                            'title': 'Okta application URL',
                            'type': 'string'
                        },
                        {
                            'name': 'gui2_url',
                            'title': 'Axonius GUI URL',
                            'type': 'string'
                        }
                    ],
                    'required': ['enabled', 'client_id', 'client_secret', 'url', 'gui2_url'],
                    'name': 'okta_login_settings',
                    'title': 'Okta Login Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Allow LDAP logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'dc_address',
                            'title': 'The host domain controller IP or DNS',
                            'type': 'string'
                        },
                        {
                            'name': 'group_cn',
                            'title': 'Group the user must be part of',
                            'type': 'string'
                        },
                        {
                            'name': 'use_group_dn',
                            'title': 'Match group name by DN',
                            'type': 'bool'
                        },
                        {
                            'name': 'default_domain',
                            'title': 'Default domain to present to the user',
                            'type': 'string'
                        },
                        {
                            'name': 'cache_time_in_hours',
                            'title': 'Cache time (hours)',
                            'type': 'integer'
                        },
                        *COMMON_SSL_CONFIG_SCHEMA
                    ],
                    'required': ['enabled', 'dc_address', 'use_group_dn', 'cache_time_in_hours'],
                    'name': 'ldap_login_settings',
                    'title': 'LDAP Login Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Allow SAML-based logins',
                            'type': 'bool'
                        },
                        {
                            'name': 'idp_name',
                            'title': 'Name of the identity provider',
                            'type': 'string'
                        },
                        {
                            'name': 'metadata_url',
                            'title': 'Metadata URL',
                            'type': 'string'
                        },
                        {
                            'name': 'axonius_external_url',
                            'title': 'Axonius external URL',
                            'type': 'string'
                        },
                        {
                            'name': 'sso_url',
                            'title': 'Single sign-on service URL',
                            'type': 'string'
                        },
                        {
                            'name': 'entity_id',
                            'title': 'Entity ID',
                            'type': 'string'
                        },
                        {
                            'name': 'certificate',
                            'title': 'Signing certificate (Base64 encoded)',
                            'type': 'file'
                        }
                    ],
                    'required': ['enabled', 'idp_name'],
                    'name': 'saml_login_settings',
                    'title': 'SAML-Based Login Settings',
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
                    'title': 'Mutual TLS Settings',
                    'type': 'array'
                },
            ],
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'okta_login_settings': {
                'enabled': False,
                'client_id': '',
                'client_secret': '',
                'url': 'https://yourname.okta.com',
                'gui2_url': 'https://127.0.0.1'
            },
            'ldap_login_settings': {
                'enabled': False,
                'dc_address': '',
                'default_domain': '',
                'group_cn': '',
                'use_group_dn': False,
                'cache_time_in_hours': 720,
                **COMMON_SSL_CONFIG_SCHEMA_DEFAULTS
            },
            'saml_login_settings': {
                'enabled': False,
                'idp_name': None,
                'metadata_url': None,
                'axonius_external_url': None,
                'sso_url': None,
                'entity_id': None,
                'certificate': None
            },
            SYSTEM_SETTINGS: {
                'refreshRate': 60,
                'defaultNumOfEntitiesPerPage': 20,
                'timeout_settings': {
                    'disable_remember_me': False,
                    'enabled': True,
                    'timeout': 1440
                },
                'singleAdapter': False,
                'multiLine': False,
                'defaultSort': True,
                'autoQuery': True,
                'exactSearch': True,
                ''
                'defaultColumnLimit': 2,
                'percentageThresholds': {
                    'error': 40,
                    'warning': 60,
                    'success': 100,
                }
            },
            'mutual_tls_settings': {
                'enabled': False,
                'mandatory': False,
                'ca_certificate': None
            }
        }

    def _get_entity_count(self, entity, mongo_filter, history, quick):
        return str(get_entities_count(mongo_filter, self.get_appropriate_view(history, entity),
                                      history_date=history, quick=quick))

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name == 'clear_dashboard_cache':
            self._clear_dashboard_cache(clear_slow=post_json is not None and post_json.get('clear_slow') is True)

            # Don't clean too often!
            time.sleep(5)
            return ''

        elif job_name == 'execute':
            # GUI is a post correlation plugin, thus this is called near the end of the cycle
            self._trigger('clear_dashboard_cache', blocking=False)
            self.dump_metrics()
            return self.generate_new_reports_offline()
        raise RuntimeError(f'GUI was called with a wrong job name {job_name}')

    def _invalidate_sessions(self, user_id: str = None):
        """
        Invalidate all sessions for this user except the current one
        """
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
            if user and (not user_id or str(d['user'].get('_id')) == user_id):
                d['user'] = None

    @property
    def get_session(self):
        return session

    @property
    def saml_settings_file_path(self):
        return SAML_SETTINGS_FILE_PATH
