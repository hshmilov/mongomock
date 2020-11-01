# pylint: disable=too-many-lines
from base64 import b64encode
import os
import datetime
from collections import defaultdict
import traceback
import re
import random
from multiprocessing.pool import ThreadPool
from threading import Lock

import OpenSSL
import requests
from pymongo.collection import Collection
from pymongo import UpdateOne

from axonius.consts.scheduler_consts import SCHEDULER_CONFIG_NAME
from axonius.consts.system_consts import WEAVE_NETWORK, DB_KEY_PATH, AXONIUS_SETTINGS_PATH, REDIS_PASSWORD_KEY, \
    REDIS_CONF_FILE_PATH, REDIS_SETTINGS_PATH, REDIS_CA_PATH, REDIS_CRT_PATH, REDIS_KEY_PATH
from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS_LEGACY_COLLECTION, GUI_PLUGIN_NAME, \
    AXONIUS_SETTINGS_DIR_NAME, GUI_SYSTEM_CONFIG_COLLECTION, NODE_ID, PLUGIN_NAME, \
    PLUGIN_UNIQUE_NAME, CORE_UNIQUE_NAME, NOTIFICATIONS_COLLECTION, AUDIT_COLLECTION, PASSWORD_MANGER_CYBERARK_VAULT, \
    PASSWORD_MANGER_ENUM, CYBERARK_DOMAIN, CYBERARK_CERT_KEY, PASSWORD_MANGER_THYCOTIC_SS_VAULT, THYCOTIC_SS_HOST, \
    THYCOTIC_SS_PORT, THYCOTIC_SS_USERNAME, THYCOTIC_SS_PASSWORD, THYCOTIC_SS_VERIFY_SSL, CYBERARK_APP_ID, \
    CYBERARK_PORT, VAULT_SETTINGS, PASSWORD_MANGER_ENABLED, CONFIG_SCHEMAS_LEGACY_COLLECTION, \
    ADAPTER_SCHEMA_LEGACY_COLLECTION, ADAPTER_SETTINGS_LEGACY_COLLECTION, DISCOVERY_REPEAT_ON, DISCOVERY_CONFIG_NAME, \
    HISTORY_REPEAT_EVERY_DAY, HISTORY_REPEAT_RECURRENCE, HISTORY_REPEAT_WEEKDAYS, HISTORY_REPEAT_ON,\
    HISTORY_REPEAT_TYPE, HISTORY_REPEAT_EVERY_LIFECYCLE, WEEKDAYS, ENABLE_CUSTOM_DISCOVERY, CONNECTION_DISCOVERY,\
    ADAPTER_DISCOVERY, DISCOVERY_REPEAT_TYPE, DISCOVERY_REPEAT_EVERY, DISCOVERY_REPEAT_RATE,\
    DISCOVERY_RESEARCH_DATE_TIME, DISCOVERY_REPEAT_EVERY_DAY, DISCOVERY_REPEAT_ON_WEEKDAYS,\
    PASSWORD_MANGER_AWS_SM_VAULT, AWS_SM_SECRET_ACCESS_KEY, AWS_SM_ACCESS_KEY_ID, AWS_SM_REGION,\
    SYSTEM_SCHEDULER_PLUGIN_NAME, HISTORY_REPEAT_TIME, HISTORY_CONFIG_NAME

from axonius.consts.adapter_consts import ADAPTER_PLUGIN_TYPE, LAST_FETCH_TIME, VAULT_PROVIDER, CLIENT_CONFIG, \
    CLIENT_ID, LEGACY_VAULT_PROVIDER
from axonius.consts.core_consts import CORE_CONFIG_NAME, NotificationHookType, LINK_REGEX
from axonius.db_migrations import db_migration
from axonius.entities import EntityType
from axonius.utils.hash import get_preferred_quick_adapter_id
from axonius.utils import datetime
from axonius.utils.encryption.mongo_encrypt import MONGO_MASTER_KEY_SIZE
from axonius.modules.plugin_settings import Consts
from axonius.redis.redis_encrypt import REDIS_PASSWORD_SIZE
from axonius.plugin_base import random_string
from services.plugin_service import PluginService, API_KEY_HEADER, UNIQUE_KEY_PARAM
from services.ports import DOCKER_PORTS
from services.system_service import SystemService
from services.updatable_service import UpdatablePluginMixin


class CoreService(PluginService, SystemService, UpdatablePluginMixin):
    def __init__(self):
        super().__init__('core')

    def _migrate_db(self):
        super()._migrate_db()
        self._run_all_migrations()

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS[CORE_UNIQUE_NAME], '443')] if os.getenv('PROD') != 'True' else []

    @db_migration(raise_on_failure=False)
    def _update_schema_version_1(self):
        print('Upgrade to schema 1')
        config_match = {
            'config_name': CORE_CONFIG_NAME
        }
        config_collection = self.db.get_collection(self.plugin_name, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION)
        current_config = config_collection.find_one(config_match)
        if current_config:
            maintenance_config = current_config['config'].get('maintenance_settings')
            if maintenance_config:
                self.db.get_collection(GUI_PLUGIN_NAME, GUI_SYSTEM_CONFIG_COLLECTION).insert_one({
                    'type': 'maintenance',
                    'provision': maintenance_config.get('analytics', True),
                    'analytics': maintenance_config.get('analytics', True),
                    'troubleshooting': maintenance_config.get('troubleshooting', True),
                    'timeout': None
                })
            del current_config['config']['maintenance_settings']
            config_collection.replace_one(config_match, current_config)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_2(self):
        print('Upgrade to schema 2')
        registered_plugins = list(self.db.client['core']['configs'].find({'plugin_type': ADAPTER_PLUGIN_TYPE}))

        # Due to old bugs, we sometimes have multiple versions of the same adapter, running on the same node.
        # However, an adapter should be a singleton on a specific node. This is why we deprecate old instances
        # here.

        plugins_mapping = defaultdict(lambda: defaultdict(list))
        for x in registered_plugins:
            if NODE_ID not in x:
                # This is a plugin that was not seen for an extremely large time
                print(f'Deprecating {x[PLUGIN_UNIQUE_NAME]}')
                self.db.deprecate_a_leftover_db(x[PLUGIN_UNIQUE_NAME])
                continue
            plugins_mapping[x[NODE_ID]][x[PLUGIN_NAME]].append(x)

        for node_id, node_plugins in plugins_mapping.items():
            for plugin_name, all_plugin_name_instances_per_node in node_plugins.items():
                if len(all_plugin_name_instances_per_node) == 1:
                    continue

                last_seen = max(
                    all_plugin_name_instances_per_node,
                    key=lambda adapter_candidate:
                    adapter_candidate.get('last_seen') or datetime.datetime(year=2017, month=1, day=1)
                )
                leftover_adapters = [
                    x[PLUGIN_UNIQUE_NAME]
                    for x
                    in all_plugin_name_instances_per_node
                    if x[PLUGIN_UNIQUE_NAME] != last_seen[PLUGIN_UNIQUE_NAME]
                ]

                print(f'Node {node_id}: {last_seen[PLUGIN_UNIQUE_NAME]} is the newest, olds are all others: ' +
                      ', '.join(leftover_adapters))

                for leftover in leftover_adapters:
                    print(f'Deprecating {leftover}')
                    self.db.deprecate_a_leftover_db(leftover)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_3(self):
        # https://axonius.atlassian.net/browse/AX-4606
        print('Upgrade to schema 3')
        # This makes the strong assumption that this deployment of axonius has only a master and no nodes

        node_id = self.node_id
        if not node_id:
            print(f'Core is not registered, nothing to do here')
            self.db_schema_version = 3
            return

        plugins_collection: Collection = self.db.client[CORE_UNIQUE_NAME]['configs']
        actions_collection: Collection = self.db.client['reports']['saved_actions']

        update_res = actions_collection.update_many(filter={
            'action.config.instance': {
                '$exists': True
            }
        }, update={
            '$set': {
                'action.config.instance': node_id
            }
        })
        print(f'Updated {update_res.modified_count} saved actions, matched {update_res.matched_count}')

        update_res = plugins_collection.update_many(filter={
            PLUGIN_UNIQUE_NAME: {
                '$ne': CORE_UNIQUE_NAME
            }
        }, update={
            '$set': {
                NODE_ID: f'!{node_id}'
            }
        })

        print(f'Updated {update_res.modified_count} plugins, matched {update_res.matched_count}')

    def perform_quick_register(self, doc: dict) -> requests.Response:
        """
        Performs a POST register call to Core
        :param doc: the doc to transfer
        """
        return requests.post(f'{self.req_url}/quick_register', json=doc)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_4(self):
        # https://axonius.atlassian.net/browse/AX-4732
        # https://axonius.atlassian.net/browse/AX-4733
        print('Upgrade to schema 4')

        stress_res = self.db.client['core']['configs'].delete_many({
            PLUGIN_NAME: 'stresstest_adapter'
        })
        stressuser_res = self.db.client['core']['configs'].delete_many({
            PLUGIN_NAME: 'stresstest_users_adapter'
        })
        print(f'Deleted {stress_res.deleted_count} stresstest and {stressuser_res.deleted_count} user stresstest')

        pm_status = self.db.client['core']['configs'].delete_many({
            PLUGIN_NAME: 'pm_status'
        })
        print(f'Deleted {pm_status.deleted_count} pm status')

        careful_exec = self.db.client['core']['configs'].delete_many({
            PLUGIN_NAME: 'careful_execution_correlator'
        })
        print(f'Deleted {careful_exec.deleted_count} careful exection')

        # Even if we delete too much, that's not really an issue, because it will just re-register
        old_stuff = self.db.client['core']['configs'].delete_many({
            'last_seen': {
                '$lt': datetime.datetime.now() - datetime.timedelta(days=30)
            }
        })
        print(f'Deleted {old_stuff.deleted_count} old stuff')

    @db_migration(raise_on_failure=False)
    def _update_schema_version_5(self):
        # https://axonius.atlassian.net/browse/AX-5222
        # This fixes the hyperlinks by removing all existing hyperlinks data and allowing
        # the system to replace it with new data.
        # This is only needed once because of historical changes that caused issues with clients.
        print('Upgrade to schema 5')
        devices_field_col = self.db.client['aggregator']['devices_fields']
        users_field_col = self.db.client['aggregator']['users_fields']

        devices_res = devices_field_col.delete_many({
            'name': 'hyperlinks'
        })
        users_res = users_field_col.delete_many({
            'name': 'hyperlinks'
        })
        print(f'Deleted {devices_res.deleted_count} hyperlinks for devices and {users_res.deleted_count} '
              f'hyperlinks for users')

    def _fix_db_for_entity(self, entity_type: EntityType):
        col = self._entity_db_map[entity_type]
        estimated_count = col.estimated_document_count()
        start_time = datetime.datetime.now()
        print(f'Fixing for entity {entity_type}, count is {estimated_count}, starting at {start_time}')

        class Expando:
            pass

        o = Expando()

        o.counter = 0
        o.adapter_entities_counter = 0
        lock = Lock()
        cursor = col.find({
            'adapters': {
                '$elemMatch': {
                    'quick_id': {
                        '$exists': False
                    }
                }
            }
        }, projection={
            f'adapters.{PLUGIN_UNIQUE_NAME}': True,
            'adapters.data.id': True,
            '_id': True
        })

        def process_entity(entity):
            for adapter in entity['adapters']:
                col.update_one({
                    '_id': entity['_id'],
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: adapter[PLUGIN_UNIQUE_NAME],
                            'data.id': adapter['data']['id']
                        }
                    }
                }, {
                    '$set': {
                        'adapters.$.quick_id': get_preferred_quick_adapter_id(adapter[PLUGIN_UNIQUE_NAME],
                                                                              adapter['data']['id'])
                    }
                })
                with lock:
                    o.adapter_entities_counter += 1

            with lock:
                o.counter += 1
                if o.counter % 2000 == 0:
                    print(f'{o.counter} out of {estimated_count} completed, {(o.counter / estimated_count) * 100}%, '
                          f'took {(datetime.datetime.now() - start_time).total_seconds()} seconds')

        with ThreadPool(30) as pool:
            pool.map(process_entity, cursor)

        total_seconds = (datetime.datetime.now() - start_time).total_seconds()
        print(f'Took {total_seconds} seconds, {o.counter / total_seconds} entities/second, '
              f'total of {o.adapter_entities_counter} adapte entities, '
              f'{o.adapter_entities_counter / total_seconds} adapter entities/second')

    @db_migration(raise_on_failure=False)
    def _update_schema_version_6(self):
        # Adds 'quick_id' to all entities in users/devices db
        print('Upgrade to schema 6')
        self._fix_db_for_entity(EntityType.Devices)
        self._fix_db_for_entity(EntityType.Users)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_7(self):
        # https://axonius.atlassian.net/browse/AX-5394
        # DB is corrupted for some customers (and demo-latest)
        print('Upgrade to schema 7')
        config_match = {
            'config_name': CORE_CONFIG_NAME
        }
        config_collection = self.db.get_collection(self.plugin_name, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION)
        current_config = config_collection.find_one(config_match)
        if current_config:
            ssl_trust_setting = current_config['config'].get('ssl_trust_settings')
            if ssl_trust_setting and not isinstance(ssl_trust_setting.get('ca_files'), list):
                ssl_trust_setting['ca_files'] = []
                config_collection.replace_one(config_match, current_config)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_8(self):
        # https://axonius.atlassian.net/browse/AX-5109
        print('Upgrade to schema 8')
        try:
            print('Creating DB encryption key')
            self.create_db_encryption_key()
            # Encrypt plugins creds
            plugins = self.db.client['core']['configs'].find(
                {
                    'plugin_type': 'Adapter'
                })
            for plugin in plugins:
                plugin_unique_name = plugin.get('plugin_unique_name')
                clients = self.db.client[plugin_unique_name]['clients'].find({})
                for client in clients:
                    client_config = client['client_config']
                    for key, val in client_config.items():
                        if client_config[key]:
                            client_config[key] = self.db_encrypt(plugin_unique_name, client_config[key])
                    self.db.client[plugin_unique_name]['clients'].update(
                        {
                            '_id': client['_id']
                        },
                        {
                            '$set':
                                {
                                    'client_config': client_config
                                }
                        })
            self.db_schema_version = 8
        except OSError as e:
            print('Cannot upgrade db to version 8, libmongocrypt error')
            raise

    @db_migration(raise_on_failure=False)
    def _update_schema_version_9(self):
        # Change client_id + set schema fetch_system_status as True
        print('Upgrade to schema 9 - Tanium adapter schema')
        # Get a list of all tanium adapters in the systems (we could have a couple - each on a different node)
        all_tanium_plugins = self.db.client['core']['configs'].find(
            {
                'plugin_name': 'tanium_adapter'
            })
        for tanium_plugin in all_tanium_plugins:
            plugin_unique_name = tanium_plugin.get('plugin_unique_name')
            clients = self.db.client[plugin_unique_name]['clients'].find({})
            # These are all the clients ("connections"). Each one of them is encrypted, so we'd have to
            # decrypt that.
            for client in clients:
                new_client_config = client['client_config'].copy()
                self.decrypt_dict(new_client_config)

                # Set a default value for the fetch_system_status key
                new_client_config['fetch_system_status'] = True

                # Re-build the client_id as the tanium adapter needs it.
                domain = new_client_config.get('domain') or ''
                username = new_client_config.get('username') or ''
                fetch_system_status = new_client_config.get('fetch_system_status', True)
                fetch_discovery = (new_client_config.get('fetch_discovery') or False)
                asset_dvc = new_client_config.get('asset_dvc')
                sq_name = new_client_config.get('sq_name')

                new_client_id = '_'.join([
                    f'{domain}',
                    f'{username}',
                    f'status-{fetch_system_status}',
                    f'asset-{asset_dvc}',
                    f'disco-{fetch_discovery}',
                    f'sq-{sq_name}',
                ])

                # Update the client
                self.encrypt_dict(plugin_unique_name, new_client_config)
                self.db.client[plugin_unique_name]['clients'].update(
                    {
                        '_id': client['_id']
                    },
                    {
                        '$set':
                            {
                                'client_id': new_client_id,
                                'client_config': new_client_config
                            }
                    })

    # pylint:disable=too-many-locals,too-many-statements,too-many-branches
    @db_migration(raise_on_failure=False)
    def _update_schema_version_10(self):
        print('Update to schema 10 - modernize file-based adapters')
        csv_adapters = list(self.db.client['core']['configs'].find({PLUGIN_NAME: 'csv_adapter'}))
        fp_csv_adapters = list(self.db.client['core']['configs'].find({PLUGIN_NAME: 'forcepoint_csv_adapter'}))
        nessus_csv_adapters = list(self.db.client['core']['configs'].find({PLUGIN_NAME: 'nessus_csv_adapter'}))
        masscan_adapters = list(self.db.client['core']['configs'].find({PLUGIN_NAME: 'masscan_adapter'}))
        nmap_adapters = list(self.db.client['core']['configs'].find({PLUGIN_NAME: 'nmap_adapter'}))

        csv_names = [doc[PLUGIN_UNIQUE_NAME] for doc in csv_adapters]
        fp_csv_names = [doc[PLUGIN_UNIQUE_NAME] for doc in fp_csv_adapters]
        nessus_csv_names = [doc[PLUGIN_UNIQUE_NAME] for doc in nessus_csv_adapters]
        masscan_names = [doc[PLUGIN_UNIQUE_NAME] for doc in masscan_adapters]
        nmap_names = [doc[PLUGIN_UNIQUE_NAME] for doc in nmap_adapters]
        puns = csv_names + nessus_csv_names + nmap_names + fp_csv_names + masscan_names
        for plugin_unique_name in puns:
            for client in self.db.client[plugin_unique_name]['clients'].find({}):
                client_config = client['client_config']
                client_config_new = client_config.copy()
                # explicitly verify user_id
                client_config_id = client_config.get('user_id')
                message_prefix = f'[GENERIC_FILE_MIGRATION] - {plugin_unique_name} -'
                if not client_config_id:
                    raise Exception(f'ERROR: Expected user_id, got {client_config_id} instead.')
                # is_users
                if 'is_users_csv' in client_config:
                    client_config_new['is_users'] = client_config.get('is_users_csv')
                configured_items = list()
                # http -> resource_path
                resource_path = None
                if 'csv_http' in client_config:
                    resource_path = client_config.get('csv_http')
                elif 'masscan_http' in client_config:
                    resource_path = client_config.get('masscan_http')
                elif 'nmap_http' in client_config:
                    resource_path = client_config.get('nmap_http')
                if resource_path:
                    client_config_new['resource_path'] = resource_path
                    configured_items.append('HTTP')
                # reset resource path to prevent false positive
                resource_path = None
                # handle smb
                # if http is configured but also smb, print a warning
                if 'csv_share' in client_config:
                    resource_path = client_config.get('csv_share')
                elif 'masscan_share' in client_config:
                    resource_path = client_config.get('masscan_share')
                elif 'nmap_share' in client_config:
                    resource_path = client_config.get('nmap_share')
                if resource_path:
                    configured_items.append('SMB Share')
                    if 'HTTP' in configured_items:
                        print(f'{message_prefix} identified both URL and SMB share')
                    else:
                        print(f'{message_prefix} Setting SMB share (http not configured)')
                        client_config_new['resource_path'] = resource_path
                # username - ignored if http is used
                username = None
                if 'csv_share_username' in client_config:
                    username = client_config.get('csv_share_username')
                elif 'nmap_share_username' in client_config:
                    username = client_config.get('nmap_share_username')
                elif 'masscan_share_username' in client_config:
                    username = client_config.get('masscan_share_username')
                if username:
                    configured_items.append('SMB Username')
                    if 'HTTP' in configured_items:
                        print(f'{message_prefix} identified both URL and SMB username')
                    else:
                        print(f'{message_prefix} Setting SMB username (http not configured)')
                        client_config_new['username'] = username
                # password - ignored if http is used
                password = None
                if 'csv_share_password' in client_config:
                    password = client_config.get('csv_share_password')
                elif 'nmap_share_password' in client_config:
                    password = client_config.get('nmap_share_password')
                elif 'masscan_share_password' in client_config:
                    password = client_config.get('masscan_share_password')
                if password:
                    configured_items.append('SMB Password')
                    if 'HTTP' in configured_items:
                        print(f'{message_prefix} identified both URL and SMB password')
                    else:
                        print(f'{message_prefix} Setting SMB password (http not configured)')
                        client_config_new['password'] = password
                if client_config.get('s3_bucket'):
                    configured_items.append('S3 Bucket')
                    print(f'{message_prefix} Identified s3 bucket')
                # file path
                file_path = None
                if 'csv' in client_config:
                    file_path = client_config.get('csv')
                elif 'masscan_file' in client_config:
                    file_path = client_config.get('masscan_file')
                elif 'nmap_file' in client_config:
                    file_path = client_config.get('nmap_file')
                if file_path:
                    configured_items.append('File Path')
                    client_config_new['file_path'] = file_path
                    if 'S3 Bucket' in configured_items:
                        print(f'{message_prefix} Identified both upload file and S3 config')
                self.db.client[plugin_unique_name]['clients'].update(
                    {
                        '_id': client['_id']
                    },
                    {
                        '$set': {
                            'client_config': client_config_new
                        }
                    }
                )
                print(f'{message_prefix} Summary - '
                      f'Identified configuration for {",".join(configured_items)}')

    @db_migration(raise_on_failure=False)
    def _update_schema_version_11(self):
        # Change client_id
        print('Upgrade to schema 11 - Qualys Scans adapter schema')
        # Get a list of all tanium adapters in the systems (we could have a couple - each on a different node)
        all_qualys_scans = self.db.client['core']['configs'].find(
            {
                'plugin_name': 'qualys_scans_adapter'
            })
        for qualys_scans in all_qualys_scans:
            plugin_unique_name = qualys_scans.get('plugin_unique_name')
            clients = self.db.client[plugin_unique_name]['clients'].find({})
            # These are all the clients ("connections"). Each one of them is encrypted, so we'd have to
            # decrypt that.
            for client in clients:
                new_client_config = client['client_config'].copy()
                self.decrypt_dict(new_client_config)

                domain = new_client_config.get('Qualys_Scans_Domain')
                username = new_client_config.get('username')

                if not domain or not username:
                    continue

                new_client_id = f'{domain}_{username}'

                self.db.client[plugin_unique_name]['clients'].update(
                    {
                        '_id': client['_id']
                    },
                    {
                        '$set':
                            {
                                'client_id': new_client_id,
                            }
                    })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_12(self):
        """
        AX-6305 Fix corrupted value for setting 'ldap_field_to_exclude'
        """
        print('Update to schema 12 - Active Directory valid value for config "ldap_field_to_exclude"')
        config_match = {
            'config_name': 'ActiveDirectoryAdapter'
        }
        all_ad_adapters = self.db.client['core']['configs'].find({
            'plugin_name': 'active_directory_adapter'
        })
        for ad_adapter in all_ad_adapters:
            plugin_unique_name = ad_adapter.get(PLUGIN_UNIQUE_NAME)
            config_collection = self.db.get_collection(plugin_unique_name, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION)
            current_config = config_collection.find_one(config_match)
            if current_config:
                ldap_exclude_config = current_config['config'].get('ldap_field_to_exclude')
                if not isinstance(ldap_exclude_config, list):
                    config_collection.update_one(config_match, {
                        '$set': {
                            f'config.ldap_field_to_exclude': []
                        }
                    })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_13(self):
        # Change client_id
        print('Upgrade to schema 13 - Split Tanium to sub-adapters')
        # Get a list of all tanium adapters in the systems (we could have a couple - each on a different node)
        all_tanium_adapters = self.db.client['core']['configs'].find(
            {
                'plugin_name': 'tanium_adapter'
            })

        tanium_asset_adapter_creds = []
        tanium_discover_adapter_creds = []
        tanium_sq_adapter_creds = []

        for tanium_adapter in all_tanium_adapters:
            plugin_unique_name = tanium_adapter.get('plugin_unique_name')
            clients = self.db.client[plugin_unique_name]['clients'].find({})
            # These are all the clients ("connections"). Each one of them is encrypted, so we'd have to
            # decrypt that.
            for client in clients:
                new_client_config = client['client_config'].copy()
                self.decrypt_dict(new_client_config)

                domain = new_client_config.get('domain') or ''
                username = new_client_config.get('username') or ''
                password = new_client_config.get('password') or ''
                verify_ssl = new_client_config.get('verify_ssl') or False
                https_proxy = new_client_config.get('https_proxy') or ''

                shared_new_client_config = {
                    'domain': domain,
                    'username': username,
                    'password': password,
                    'verify_ssl': verify_ssl,
                    'https_proxy': https_proxy
                }

                fetch_discovery = new_client_config.get('fetch_discovery')

                if fetch_discovery:
                    tanium_discover_adapter_creds.append({
                        'client_config': shared_new_client_config.copy(),
                        'status': client.get('status') or 'success',
                        'error': client.get('error')
                    })

                asset_dvc = new_client_config.get('asset_dvc')
                if asset_dvc:
                    asset_new_client_config = shared_new_client_config.copy()
                    asset_new_client_config['asset_dvc'] = asset_dvc
                    tanium_asset_adapter_creds.append(
                        {
                            'client_config': asset_new_client_config,
                            'status': client.get('status') or 'success',
                            'error': client.get('error')
                        }
                    )

                sq_name = new_client_config.get('sq_name') or ''
                sq_refresh = new_client_config.get('sq_refresh')
                sq_max_hours = new_client_config.get('sq_max_hours')

                if sq_name:
                    sq_new_client_config = shared_new_client_config.copy()
                    sq_new_client_config['sq_name'] = sq_name
                    sq_new_client_config['sq_refresh'] = sq_refresh if sq_refresh is not None else False
                    sq_new_client_config['sq_max_hours'] = sq_max_hours if sq_max_hours is not None else 6
                    sq_new_client_config['no_results_wait'] = True
                    tanium_sq_adapter_creds.append(
                        {
                            'client_config': sq_new_client_config,
                            'status': client.get('status') or 'success',
                            'error': client.get('error')
                        }
                    )

        # self.encrypt_dict(plugin_unique_name, new_client_config)
        for i, creds in enumerate(tanium_asset_adapter_creds):
            print(f'Migrating {i + 1} / {len(tanium_asset_adapter_creds)} Tanium asset adapter')
            creds_client_config = creds['client_config']
            creds['client_id'] = f'{creds_client_config.get("domain")}_' \
                                 f'{creds_client_config.get("username")}_{creds_client_config.get("asset_dvc")}'
            self.encrypt_dict('tanium_asset_adapter_0', creds['client_config'])
            self.db.client['tanium_asset_adapter_0']['clients'].insert_one(creds)

        for i, creds in enumerate(tanium_discover_adapter_creds):
            print(f'Migrating {i + 1} / {len(tanium_discover_adapter_creds)} Tanium discover adapter')
            creds_client_config = creds['client_config']
            creds['client_id'] = f'{creds_client_config.get("domain")}_{creds_client_config.get("username")}'
            self.encrypt_dict('tanium_discover_adapter_0', creds['client_config'])
            self.db.client['tanium_discover_adapter_0']['clients'].insert_one(creds)

        for i, creds in enumerate(tanium_sq_adapter_creds):
            print(f'Migrating {i + 1} / {len(tanium_sq_adapter_creds)} Tanium sq adapter')
            creds_client_config = creds['client_config']
            creds['client_id'] = f'{creds_client_config.get("domain")}_{creds_client_config.get("username")}' \
                                 f'_{creds_client_config.get("sq_name")}'
            self.encrypt_dict('tanium_sq_adapter_0', creds['client_config'])
            self.db.client['tanium_sq_adapter_0']['clients'].insert_one(creds)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_14(self):
        # Change client_id + set schema fetch_system_status as True
        # Get a list of all tanium adapters in the systems (we could have a couple - each on a different node)
        all_tanium_plugins = self.db.client['core']['configs'].find(
            {
                'plugin_name': 'tanium_adapter'
            })
        for tanium_plugin in all_tanium_plugins:
            plugin_unique_name = tanium_plugin.get('plugin_unique_name')
            clients = self.db.client[plugin_unique_name]['clients'].find({})
            # These are all the clients ("connections"). Each one of them is encrypted, so we'd have to
            # decrypt that.
            for client in clients:
                new_client_config = client['client_config'].copy()
                self.decrypt_dict(new_client_config)

                # Re-build the client_id as the tanium adapter needs it.
                domain = new_client_config.get('domain')
                username = new_client_config.get('username')
                if not domain or not username:
                    continue

                # Update the client
                self.db.client[plugin_unique_name]['clients'].update(
                    {
                        '_id': client['_id']
                    },
                    {
                        '$set':
                            {
                                'client_id': f'{domain}_{username}',
                            }
                    })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_15(self):
        print('Upgrade to schema 15 - Notifications hooks Refactor')
        notifications_collection = self.db.get_collection(self.plugin_name, NOTIFICATIONS_COLLECTION)
        notifications_filter = {
            'content': {
                '$regex': LINK_REGEX
            }
        }
        notifications = notifications_collection.find(notifications_filter)
        db_bulk_actions = []

        if notifications.count() > 0:
            for notification_document in notifications:
                hooks, notification_content = replace_notification_content_with_hooks(
                    notification_document['content'],
                    LINK_REGEX)
                if len(hooks) > 0:
                    db_bulk_actions.append(UpdateOne({'_id': notification_document['_id']},
                                                     {'$set': {
                                                         'hooks': hooks,
                                                         'content': notification_content
                                                     }}))

            notifications_collection.bulk_write(db_bulk_actions)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_16(self):
        print('Upgrade to schema 16 - Audit max size and documents')
        max_documents = 100000
        core_db = self.db.get_database('core')
        new_audit_collection = core_db.create_collection('audit_temp', capped=True, size=100000000,
                                                         max=max_documents)
        if AUDIT_COLLECTION in core_db.list_collection_names():
            old_audit_collection = self.db.get_collection(self.plugin_name, AUDIT_COLLECTION)
            old_audit_collection.aggregate([
                {'$match': {}},
                {'$sort': {'timestamp': -1}},
                {'$limit': max_documents},
                {'$merge': {'into': 'audit_temp'}}
            ], allowDiskUse=True)
            old_audit_collection.drop()

        new_audit_collection.rename(AUDIT_COLLECTION)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_17(self):
        # enterprise password mgmt - vault settings
        print('Upgrade to schema 17 -enterprise password mgmt - vault settings ')
        config_match = {
            'config_name': CORE_CONFIG_NAME
        }

        updated_vault_settings = {
            PASSWORD_MANGER_ENABLED: False,
            PASSWORD_MANGER_ENUM: PASSWORD_MANGER_AWS_SM_VAULT,
            PASSWORD_MANGER_CYBERARK_VAULT: {
                CYBERARK_DOMAIN: None,
                CYBERARK_PORT: None,
                CYBERARK_APP_ID: None,
                CYBERARK_CERT_KEY: None
            },
            PASSWORD_MANGER_THYCOTIC_SS_VAULT: {
                THYCOTIC_SS_HOST: None,
                THYCOTIC_SS_PORT: None,
                THYCOTIC_SS_USERNAME: None,
                THYCOTIC_SS_PASSWORD: None,
                THYCOTIC_SS_VERIFY_SSL: False
            },
            PASSWORD_MANGER_AWS_SM_VAULT: {
                AWS_SM_ACCESS_KEY_ID: None,
                AWS_SM_SECRET_ACCESS_KEY: None,
                AWS_SM_REGION: None,
            }
        }

        config_collection = self.db.get_collection(self.plugin_name, CONFIGURABLE_CONFIGS_LEGACY_COLLECTION)
        current_config = config_collection.find_one(config_match)

        if current_config:
            current_vault_settings = current_config['config'].get(VAULT_SETTINGS)
            if current_vault_settings and current_vault_settings.get(PASSWORD_MANGER_ENABLED):
                updated_vault_settings[PASSWORD_MANGER_ENABLED] = True
                current_vault_settings.pop(PASSWORD_MANGER_ENABLED)
                updated_vault_settings[PASSWORD_MANGER_CYBERARK_VAULT] = current_vault_settings
                current_config['config'][VAULT_SETTINGS] = updated_vault_settings
                config_collection.replace_one(config_match, current_config)
            else:
                current_config['config'][VAULT_SETTINGS] = updated_vault_settings
                config_collection.replace_one(config_match, current_config)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_18(self):
        print(f'Upgrading to schema version 18 - Nexpose adapter')
        nexpose_adapters = list(self.db.client['core']['configs'].find({PLUGIN_NAME: 'nexpose_adapter'}))
        nexpose_plugin_unique_names = [doc[PLUGIN_UNIQUE_NAME] for doc in nexpose_adapters]

        advanced_settings = None

        # 1. get advanced settings
        for plugin_unique_name in nexpose_plugin_unique_names:
            # Take the first one we find. It should be the same for all plugins
            advanced_settings = self.db.client[plugin_unique_name][CONFIGURABLE_CONFIGS_LEGACY_COLLECTION].find_one(
                {
                    'config_name': 'NexposeAdapter'
                }
            )

            if advanced_settings:
                advanced_settings = advanced_settings.get('config') or {}
                break

        if not advanced_settings:
            print(f'Warning - no advanced settings found for nexpose. Continuing')
            self.db_schema_version = 18
            return

        for plugin_unique_name in nexpose_plugin_unique_names:
            # Go over all the different nexpose plugin unique names we have. If we have
            # clients there then we must add some configurations to this client.

            for client in self.db.client[plugin_unique_name]['clients'].find():
                # If we found this client, we have
                new_client_config = client['client_config'].copy()
                self.decrypt_dict(new_client_config)

                fetch_tags_config = advanced_settings.get('fetch_tags', True)

                new_client_config['fetch_tags'] = fetch_tags_config
                new_client_config['fetch_sw'] = fetch_tags_config
                new_client_config['fetch_ports'] = fetch_tags_config
                new_client_config['fetch_policies'] = fetch_tags_config

                new_client_config['fetch_vulnerabilities'] = advanced_settings.get('fetch_vulnerabilities', False)
                new_client_config['num_of_simultaneous_devices'] = advanced_settings.get(
                    'num_of_simultaneous_devices', 50)
                new_client_config['drop_only_ip_devices'] = advanced_settings.get('drop_only_ip_devices', False)

                self.encrypt_dict(plugin_unique_name, new_client_config)
                self.db.client[plugin_unique_name]['clients'].update(
                    {
                        '_id': client['_id']
                    },
                    {
                        '$set':
                            {
                                'client_config': new_client_config
                            }
                    })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_19(self):
        print(f'Upgrading to schema version 19 - Nexpose advanced settings')
        nexpose_adapters = list(self.db.client['core']['configs'].find({PLUGIN_NAME: 'nexpose_adapter'}))
        nexpose_plugin_unique_names = [doc[PLUGIN_UNIQUE_NAME] for doc in nexpose_adapters]

        # After we have finished the clients changing let's remove the advanced config
        for plugin_unique_name in nexpose_plugin_unique_names:
            self.db.client[plugin_unique_name][CONFIGURABLE_CONFIGS_LEGACY_COLLECTION].remove(
                {
                    'config_name': 'NexposeAdapter'
                }
            )

    @db_migration(raise_on_failure=False)
    def _update_schema_version_20(self):
        print(f'Updating to schema version 20 - New Configuable Configs location')
        # To support the new format per-plugin settings, we have to move
        # 1. Configurable Configs
        # 2. Config Schemas
        # 3. Adapter Settings
        # 4. Adapter Schemas
        #
        # In case there are several adapters, we always prioritize the first one (_0)
        # In case _0 doesn't exist (old systems) we take one of them
        plugins_by_plugin_name = defaultdict(list)
        for plugin_document in self.db.client[CORE_UNIQUE_NAME]['configs'].find(
                {},
                projection={PLUGIN_NAME: 1, PLUGIN_UNIQUE_NAME: 1}
        ):
            plugin_i_name = plugin_document.get(PLUGIN_NAME)
            plugin_i_unique_name = plugin_document.get(PLUGIN_UNIQUE_NAME)
            if not plugin_i_name or not plugin_i_unique_name:
                continue
            plugins_by_plugin_name[plugin_i_name].append(plugin_i_unique_name)

        for plugin_name, plugin_unique_names in plugins_by_plugin_name.items():
            # give 0 priority, as it is usually the first one in the system
            sorted_plugin_unique_names = sorted(plugin_unique_names)

            # Take the first plugin that has configurable configs and assume it has the rest as well. This will
            # be the one that we choose for all adapters.
            chosen_plugin_unique_name = None
            for sorted_plugin_unique_name_i in sorted_plugin_unique_names:
                plugin_configurable_configs = list(
                    self.db.client[sorted_plugin_unique_name_i][CONFIGURABLE_CONFIGS_LEGACY_COLLECTION].find({})
                )
                if plugin_configurable_configs:
                    chosen_plugin_unique_name = sorted_plugin_unique_name_i
                    break

            if not chosen_plugin_unique_name:
                continue

            plugin_settings = self.db.plugins.get_plugin_settings(plugin_name)
            chosen_plugin_unique_name_db = self.db.client[chosen_plugin_unique_name]
            # Migrate configurable configs
            for configurable_config in list(
                    chosen_plugin_unique_name_db[CONFIGURABLE_CONFIGS_LEGACY_COLLECTION].find({})
            ):
                if not configurable_config.get('config_name') or not configurable_config.get('config'):
                    print(f'Exception while upgrading  - plugin {chosen_plugin_unique_name} has invalid cc')
                    continue
                plugin_settings.configurable_configs[
                    configurable_config['config_name']] = configurable_config['config']

            # Migrate config schemas
            for config_schema in list(
                    chosen_plugin_unique_name_db[CONFIG_SCHEMAS_LEGACY_COLLECTION].find({})
            ):
                if not config_schema.get('config_name') or not config_schema.get('schema'):
                    print(f'Exception while upgrading  - plugin {chosen_plugin_unique_name} has invalid cs')
                    continue
                plugin_settings.config_schemas[config_schema['config_name']] = config_schema['schema']

            # Migrate adapter schema
            adapter_schema = chosen_plugin_unique_name_db[ADAPTER_SCHEMA_LEGACY_COLLECTION].find_one({})
            if adapter_schema:
                plugin_settings.adapter_client_schema = adapter_schema['schema']

            # Migrate adapter settings
            for adapter_settings in list(
                    chosen_plugin_unique_name_db[ADAPTER_SETTINGS_LEGACY_COLLECTION].find({})
            ):
                last_fetch_time = adapter_settings.get(LAST_FETCH_TIME)
                if last_fetch_time:
                    plugin_settings.plugin_settings_keyval[LAST_FETCH_TIME] = last_fetch_time
                    break
            print(f'Successfully migrated {plugin_name}')

    @db_migration(raise_on_failure=False)
    def _update_schema_version_21(self):
        # Delete general_info plugin
        print('Upgrade to schema 21')
        delete_result = self.db.client['core']['configs'].delete_one(
            {
                'plugin_unique_name': 'general_info'
            })
        if not delete_result or delete_result.deleted_count == 0:
            print('general_info config was not deleted.')

    @db_migration(raise_on_failure=False)
    def _update_schema_version_22(self):
        # ------------------------------------------------------------- #
        # fix legacy vault provider:
        # migrate adapter's clients if any of adapter schema fields is password type
        # and contain either old cyberark or thycotic vault data.
        # client_config will be decrypt and encrypt in case of data migration
        # ------------------------------------------------------------- #
        print(f'Upgrading version 22 - fix legacy vault provider')
        adapters = self.db.client[CORE_UNIQUE_NAME]['configs'].find({'plugin_type': ADAPTER_PLUGIN_TYPE})
        for adapter in adapters:
            adapter_name = adapter[PLUGIN_UNIQUE_NAME]
            plugin_settings = self.db.plugins.get_plugin_settings(adapter[PLUGIN_NAME])
            adaper_clients_collection: Collection = self.db.client[adapter_name]['clients']
            adapter_client_schema: dict = plugin_settings.adapter_client_schema
            pwd_fields = self._get_password_fields_from_adapter_schema(adapter_client_schema)
            if not pwd_fields:
                continue

            for client in adaper_clients_collection.find({}):
                self._check_for_legacy_vault_provider_data(adapter_name,
                                                           client,
                                                           pwd_fields,
                                                           adaper_clients_collection)

    @db_migration(raise_on_failure=False)
    def _update_schema_version_23(self):
        print(f'Updating to schema version 23 - One GridFS DB')
        import gridfs
        core_fs = gridfs.GridFS(self.db.client[CORE_UNIQUE_NAME])

        for plugin_document in self.db.client[CORE_UNIQUE_NAME]['configs'].find(
                {},
                projection={PLUGIN_NAME: 1, PLUGIN_UNIQUE_NAME: 1}
        ):
            plugin_unique_name = plugin_document.get(PLUGIN_UNIQUE_NAME)
            if plugin_unique_name == CORE_UNIQUE_NAME:
                continue

            fs = gridfs.GridFS(self.db.client[plugin_unique_name])

            for file in self.db.client[plugin_unique_name].fs.files.find({}):
                try:
                    f = fs.get(file['_id'])
                    core_fs.put(f, _id=file['_id'], filename=file.get('filename'), encoding=file.get('encoding'))
                except Exception as e:
                    print(f'Exception while upgrading - '
                          f'filename {file.get("filename") or ""} in {plugin_unique_name!r} '
                          f'could not be moved: {str(e)}')

    @db_migration(raise_on_failure=False)
    def _update_schema_version_24(self):
        print(f'Updating to schema version 24 - Update adapters discovery schema')
        adapters = self.db.client[CORE_UNIQUE_NAME]['configs'].find({'plugin_type': ADAPTER_PLUGIN_TYPE})
        for adapter in adapters:
            adapter_name = adapter[PLUGIN_NAME]
            plugin_settings = self.db.plugins.get_plugin_settings(adapter_name)
            adapter_config = plugin_settings.configurable_configs
            if adapter_config.discovery_configuration is None:
                # Old version probably custom discovery not available yet
                continue
            schedule_settings = adapter_config.discovery_configuration.get(DISCOVERY_REPEAT_ON)
            if isinstance(schedule_settings, list):
                # Already migrated
                continue
            if schedule_settings:
                self.db.plugins.get_plugin_settings(adapter_name).configurable_configs.update_config(
                    'DiscoverySchema',
                    {
                        DISCOVERY_REPEAT_ON: [day[0] for day in schedule_settings.items() if day[1]]
                    }
                )

    @db_migration(raise_on_failure=False)
    def _update_schema_version_25(self):
        print(f'Updating to schema version 25 - JITA migration')
        all_jita = list(self.db.client[CORE_UNIQUE_NAME]['configs'].find({PLUGIN_NAME: 'jita_adapter'}))
        for jita_instance in all_jita:
            jita_pun = jita_instance[PLUGIN_UNIQUE_NAME]
            all_clients_for_pun = list(self.db.client[jita_pun]['clients'].find({}))
            if not all_clients_for_pun:
                # If there isn't even one single client, then delete the config
                self.db.client[CORE_UNIQUE_NAME]['configs'].delete_one({PLUGIN_UNIQUE_NAME: jita_pun})

    @db_migration(raise_on_failure=False)
    def _update_schema_version_26(self):
        print(f'Updating to schema version 26 - Qualys config migration')
        self.migrate_adapter_advanced_settings_to_connection(
            'qualys_scans_adapter',
            'qualys_tags_white_list'
        )

    @db_migration(raise_on_failure=False)
    def _update_schema_version_27(self):
        print(f'Updating to schema version 27 - historical schedule')
        configurable_configs = self.db.plugins.system_scheduler.configurable_configs
        if not configurable_configs[SCHEDULER_CONFIG_NAME]:
            # no scheduler config yet, first run
            return
        discovery_settings = configurable_configs[SCHEDULER_CONFIG_NAME].get('discovery_settings', {})
        history_enabled = discovery_settings.pop('save_history', True)
        history_retention_settings = discovery_settings.pop('history_settings', {})
        history_settings = {
            'enabled': history_enabled,
            HISTORY_REPEAT_EVERY_DAY: {
                HISTORY_REPEAT_RECURRENCE: 1
            },
            HISTORY_REPEAT_WEEKDAYS: {
                HISTORY_REPEAT_ON: [day.lower() for day in WEEKDAYS]
            },
            HISTORY_REPEAT_TYPE: HISTORY_REPEAT_EVERY_LIFECYCLE,
        }
        new_config = {
            'discovery_settings': discovery_settings,
            'history_retention_settings': history_retention_settings,
            'history_settings': history_settings
        }

        configurable_configs[SCHEDULER_CONFIG_NAME] = new_config

    @db_migration(raise_on_failure=False)
    def _update_schema_version_28(self):
        print(f'Updating to schema version 28 - Update adapters discovery schema conditional new value')

        self.db.client[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].update_many(
            {
                'config_name': DISCOVERY_CONFIG_NAME,
                'config.adapter_discovery.conditional': 'repeat_every'
            },
            {
                '$set': {
                    'config.adapter_discovery.conditional': 'system_research_date'
                }
            })

        self.db.client[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].update_many(
            {
                'config_name': DISCOVERY_CONFIG_NAME,
                'config.adapter_discovery.conditional': 'repeat_on'
            },
            {
                '$set': {
                    'config.adapter_discovery.conditional': 'system_research_weekdays'
                }
            })

    @db_migration(raise_on_failure=False)
    def _update_schema_version_29(self):
        print(f'Updating to schema version 29')
        configs_to_fix = self.db.client[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].find(
            {
                'config_name': DISCOVERY_CONFIG_NAME,
            })
        for discovery_config in configs_to_fix:
            config = discovery_config.get('config', {})
            # we need to fix this config
            if ENABLE_CUSTOM_DISCOVERY in config:
                plugin_name = discovery_config.get(PLUGIN_NAME)
                repeat_type = config.get(DISCOVERY_REPEAT_TYPE)
                # migration 28
                if repeat_type == 'repeat_every':
                    repeat_type = 'system_research_date'
                if repeat_type == 'repeat_on':
                    repeat_type = 'system_research_weekdays'

                new_config = {
                    ADAPTER_DISCOVERY: {
                        ENABLE_CUSTOM_DISCOVERY: config.get(ENABLE_CUSTOM_DISCOVERY, False),
                        DISCOVERY_REPEAT_TYPE: repeat_type,
                        DISCOVERY_REPEAT_EVERY_DAY: {
                            DISCOVERY_REPEAT_EVERY: config.get(DISCOVERY_REPEAT_EVERY, 1),
                            DISCOVERY_RESEARCH_DATE_TIME: config.get(DISCOVERY_RESEARCH_DATE_TIME, '13:00'),
                        },
                        DISCOVERY_REPEAT_RATE: 12,
                        DISCOVERY_REPEAT_ON_WEEKDAYS: {
                            DISCOVERY_REPEAT_ON: config.get(DISCOVERY_REPEAT_ON, [day.lower() for day in WEEKDAYS]),
                            DISCOVERY_RESEARCH_DATE_TIME: config.get(DISCOVERY_RESEARCH_DATE_TIME, '13:00'),
                        }
                    },
                    CONNECTION_DISCOVERY: {
                        ENABLE_CUSTOM_DISCOVERY: False
                    }
                }
                self.db.plugins.get_plugin_settings(plugin_name).configurable_configs[DISCOVERY_CONFIG_NAME] = \
                    new_config

    @db_migration(raise_on_failure=False)
    def _update_schema_version_30(self):
        print(f'Updating to schema version 30')
        configs_to_fix = self.db.client[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].find(
            {
                'config_name': DISCOVERY_CONFIG_NAME,
            })
        for discovery_config in configs_to_fix:
            config = discovery_config.get('config', {})
            plugin_name = discovery_config.get(PLUGIN_NAME)
            repeat_on = config.get(ADAPTER_DISCOVERY, {}).get(DISCOVERY_REPEAT_ON_WEEKDAYS, {}).get(DISCOVERY_REPEAT_ON)
            if isinstance(repeat_on, dict):
                fixed_repeat_on = [day[0] for day in repeat_on.items() if day[1]]
                config[ADAPTER_DISCOVERY][DISCOVERY_REPEAT_ON_WEEKDAYS][DISCOVERY_REPEAT_ON] = fixed_repeat_on
                self.db.plugins.get_plugin_settings(plugin_name).configurable_configs[DISCOVERY_CONFIG_NAME] = config

    @db_migration(raise_on_failure=False)
    def _update_schema_version_31(self):
        print('Upgrade to schema 31')
        # fix connection custom discovery settings
        plugins = self.db.client['core']['configs'].find(
            {
                'plugin_type': ADAPTER_PLUGIN_TYPE
            })
        for plugin in plugins:
            plugin_unique_name = plugin.get(PLUGIN_UNIQUE_NAME)
            clients = self.db.client[plugin_unique_name]['clients'].find({
                f'{CONNECTION_DISCOVERY}.{DISCOVERY_REPEAT_RATE}': {
                    '$gt': 24
                }
            })
            for client in clients:
                self.db.client[plugin_unique_name]['clients'].update(
                    {
                        '_id': client['_id']
                    },
                    {
                        '$set':
                            {
                                f'{CONNECTION_DISCOVERY}.{DISCOVERY_REPEAT_RATE}': 24
                            }
                    })

        configs_to_fix = self.db.client[CORE_UNIQUE_NAME][Consts.AllConfigurableConfigs].find(
            {
                f'config.{ADAPTER_DISCOVERY}.{DISCOVERY_REPEAT_RATE}': {
                    '$gt': 24
                }
            })
        # fix adapters custom discovery settings
        for config_to_fix in configs_to_fix:
            config = config_to_fix.get('config', {})
            plugin_name = config_to_fix.get(PLUGIN_NAME)
            config[ADAPTER_DISCOVERY][DISCOVERY_REPEAT_RATE] = 24
            self.db.plugins.get_plugin_settings(plugin_name).configurable_configs[DISCOVERY_CONFIG_NAME] = \
                config

    @db_migration(raise_on_failure=False)
    def _update_schema_version_32(self):
        print('Upgrade to schema 32')
        password = self.create_redis_password()
        self.create_redis_conf_file(password)
        self.create_redis_certs()

    @db_migration(raise_on_failure=False)
    def _update_schema_version_33(self):
        print('Upgrade to schema 33')

        config = self.db.plugins.system_scheduler.configurable_configs[SCHEDULER_CONFIG_NAME]
        if not config:
            # no scheduler config yet, first run
            return

        history_config = config.get(HISTORY_CONFIG_NAME, {})
        repeat_type = history_config.get(HISTORY_REPEAT_TYPE)

        if repeat_type in [HISTORY_REPEAT_EVERY_DAY, HISTORY_REPEAT_WEEKDAYS]:
            local_machine_midnight = datetime.datetime.combine(datetime.datetime.now(), datetime.datetime.min.time())
            utc_midnight = local_machine_midnight.replace(tzinfo=None).astimezone(tz=datetime.timezone.utc)
            history_config[repeat_type][HISTORY_REPEAT_TIME] = utc_midnight.strftime('%H:%M')

            self.db.plugins.get_plugin_settings(SYSTEM_SCHEDULER_PLUGIN_NAME).configurable_configs.update_config(
                SCHEDULER_CONFIG_NAME,
                {
                    HISTORY_CONFIG_NAME: history_config
                }
            )

    @db_migration(raise_on_failure=False)
    def _update_schema_version_34(self):
        print('Upgrade to 34')
        # https://axonius.atlassian.net/browse/AX-9691
        self.migrate_adapter_advanced_settings_to_connection('okta_adapter', 'parallel_requests')

    def migrate_adapter_advanced_settings_to_connection(
            self,
            adapter_name: str,
            advanced_setting_key: str
    ):
        plugin_settings = self.db.plugins.get_plugin_settings(adapter_name)
        all_configs = plugin_settings.configurable_configs.unique_configuration or {}
        advanced_setting_val = all_configs.get(advanced_setting_key)

        if advanced_setting_val is None:
            return

        # Get all registered plugin unique names
        all_adapter_pun = [
            x[PLUGIN_UNIQUE_NAME] for x in self.db.client[CORE_UNIQUE_NAME]['configs'].find(
                {PLUGIN_NAME: adapter_name},
                projection={PLUGIN_UNIQUE_NAME: 1}
            )
        ]

        for adapter_plugin_unique_name in all_adapter_pun:
            for client in self.db.client[adapter_plugin_unique_name]['clients'].find({}):
                client_config = client.get('client_config')
                if not client_config:
                    continue

                new_client_config = client_config.copy()
                self.decrypt_dict(new_client_config)
                new_client_config[advanced_setting_key] = advanced_setting_val
                self.encrypt_dict(adapter_plugin_unique_name, new_client_config)
                self.db.client[adapter_plugin_unique_name]['clients'].update(
                    {
                        '_id': client['_id']
                    },
                    {
                        '$set':
                            {
                                'client_config': new_client_config
                            }
                    })

    def register(self, api_key=None, plugin_name=''):
        headers = {}
        params = {}
        if api_key:
            headers[API_KEY_HEADER] = api_key
            params[UNIQUE_KEY_PARAM] = plugin_name

        return requests.get(f'{self.req_url}/register', headers=headers, params=params)

    @property
    def volumes_override(self):
        # Creating a settings dir outside of cortex (on production machines
        # this will be /home/ubuntu/.axonius_settings) for login marker and weave encryption key.
        settings_path = os.path.abspath(os.path.join(self.cortex_root_dir, AXONIUS_SETTINGS_DIR_NAME))
        os.makedirs(settings_path, exist_ok=True)
        container_settings_dir_path = os.path.join('/home/axonius/', AXONIUS_SETTINGS_DIR_NAME)

        if self.docker_network == WEAVE_NETWORK:
            docker_socket_mapping = '/var/run/weave/weave.sock:/var/run/docker.sock'
        else:
            # running on a windows machine
            docker_socket_mapping = '/var/run/docker.sock:/var/run/docker.sock'
        volumes = [f'{settings_path}:{container_settings_dir_path}', docker_socket_mapping]

        # Core has all adapters exposed.
        adapters = os.path.abspath(os.path.join(self.cortex_root_dir, 'adapters'))
        volumes.append(f'{adapters}:/home/axonius/app/adapters:ro')
        volumes.extend(super().volumes_override)
        return volumes

    def _is_service_alive(self):
        try:
            r = self.version()
            return r.status_code == 200
        except Exception:
            return False

    def get_registered_plugins(self):
        return self.register()

    def set_config_legacy(self, config):
        self.db.get_collection('core', CONFIGURABLE_CONFIGS_LEGACY_COLLECTION).update_one(
            {'config_name': CORE_CONFIG_NAME},
            {'$set': config}
        )
        self.post('update_config')

    @property
    def get_max_uwsgi_threads(self) -> int:
        return 500

    @staticmethod
    def create_db_encryption_key():
        """
        Create mongo encryption master key file if it not exists
        :return: None
        """
        if not DB_KEY_PATH.is_file():
            try:
                AXONIUS_SETTINGS_PATH.mkdir(exist_ok=True)
                with open(DB_KEY_PATH, 'wb') as f:
                    key = os.urandom(MONGO_MASTER_KEY_SIZE)
                    f.write(b64encode(key))
                DB_KEY_PATH.chmod(0o646)
            except Exception as e:
                print(f'Error writing db encryption key: {e}')
                if DB_KEY_PATH.is_file():
                    DB_KEY_PATH.unlink()

    @staticmethod
    def create_redis_password():
        """
        Create redis password file if it not exists
        :return: None
        """
        key = None
        if not REDIS_PASSWORD_KEY.is_file():
            try:
                REDIS_SETTINGS_PATH.mkdir(parents=True, exist_ok=True)
                with open(REDIS_PASSWORD_KEY, 'w') as f:
                    key = random_string(REDIS_PASSWORD_SIZE)
                    f.write(key)
                REDIS_PASSWORD_KEY.chmod(0o646)
            except Exception as e:
                print(f'Error writing redis password: {e}')
                if REDIS_PASSWORD_KEY.is_file():
                    REDIS_PASSWORD_KEY.unlink()
        return key

    def create_redis_conf_file(self, password):
        """
        Create redis password file if it not exists
        :return: None
        """
        if not REDIS_CONF_FILE_PATH.is_file():
            try:
                if not password:
                    password = random_string(REDIS_PASSWORD_SIZE)
                REDIS_SETTINGS_PATH.mkdir(parents=True, exist_ok=True)
                with open(REDIS_CONF_FILE_PATH, 'w') as f:
                    redis_conf = self.redis.get_conf_file(password)
                    f.write(redis_conf)
                REDIS_CONF_FILE_PATH.chmod(0o646)
            except Exception as e:
                print(f'Error writing redis conf file: {e}')
                if REDIS_CONF_FILE_PATH.is_file():
                    REDIS_CONF_FILE_PATH.unlink()

    @staticmethod
    def create_redis_certs():
        if not REDIS_KEY_PATH.is_file() or not REDIS_CRT_PATH.is_file() or not REDIS_CA_PATH.is_file():
            try:
                # create ca.key
                ca_key = OpenSSL.crypto.PKey()
                ca_key.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)

                # Generate redis.csr
                ca_csr = OpenSSL.crypto.X509Req()
                ca_csr.get_subject().CN = 'Axonius Certificate Authority'
                ca_csr.set_pubkey(ca_key)
                ca_csr.sign(ca_key, 'sha256')  # This is redis.key

                # create ca.crt
                ca_cert = OpenSSL.crypto.X509()
                ca_cert.set_serial_number(random.randrange(100000))
                ca_cert.gmtime_adj_notBefore(0)
                ca_cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)  # 10 years
                ca_cert.set_issuer(ca_csr.get_subject())
                ca_cert.set_subject(ca_csr.get_subject())
                ca_cert.set_pubkey(ca_key)
                ca_cert.sign(ca_key, 'sha256')
                ca_cert_pem_file = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_cert)

                # create redis.key
                redis_key = OpenSSL.crypto.PKey()
                redis_key.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)
                redis_key_pem = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, redis_key)

                # Generate redis.csr
                redis_csr = OpenSSL.crypto.X509Req()
                redis_csr.get_subject().CN = 'Axonius Redis Certificate Authority'
                redis_csr.set_pubkey(redis_key)
                redis_csr.sign(redis_key, 'sha256')  # This is redis.key

                # Generate redis.crt
                redis_cert = OpenSSL.crypto.X509()
                redis_cert.set_serial_number(random.randrange(100000))
                redis_cert.gmtime_adj_notBefore(0)
                redis_cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)  # 10 years
                redis_cert.set_issuer(ca_cert.get_subject())
                redis_cert.set_subject(redis_csr.get_subject())
                redis_cert.set_pubkey(redis_csr.get_pubkey())
                redis_cert.sign(ca_key, 'sha256')
                redis_cert_pem_file = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, redis_cert)

                with open(REDIS_KEY_PATH, 'wb') as fh:
                    fh.write(redis_key_pem)
                with open(REDIS_CRT_PATH, 'wb') as fh:
                    fh.write(redis_cert_pem_file)
                with open(REDIS_CA_PATH, 'wb') as fh:
                    fh.write(ca_cert_pem_file)
            except Exception as e:
                print(f'Error creating redis certs: {e}')
                if REDIS_KEY_PATH.is_file():
                    REDIS_KEY_PATH.unlink()
                if REDIS_CRT_PATH.is_file():
                    REDIS_CRT_PATH.unlink()
                if REDIS_CA_PATH.is_file():
                    REDIS_CA_PATH.unlink()

    @staticmethod
    def _get_password_fields_from_adapter_schema(adapter_client_schema: dict) -> list:
        adapter_client_schema = adapter_client_schema or {}
        return [item['name'] for item in adapter_client_schema.get('items', []) if item.get('format') == 'password']

    def _check_for_legacy_vault_provider_data(self, adapter_name: str, adapter_client: dict,
                                              adapter_password_fields: list, adaper_clients_collection: Collection):
        try:
            client_config_copy = adapter_client.get(CLIENT_CONFIG).copy()
            self.decrypt_dict(client_config_copy)
            save_to_db = False
            client_id = adapter_client[CLIENT_ID]

            for pwd_field in adapter_password_fields:
                if not isinstance(client_config_copy.get(pwd_field), dict):
                    continue

                if (client_config_copy[pwd_field]['type'] == LEGACY_VAULT_PROVIDER or
                        isinstance(client_config_copy[pwd_field].get('query'), str)):
                    print(f'Updating Adapter:{adapter_name} Client:{client_id} '
                          f'found with legacy cyberark vault data field {pwd_field}')
                    client_config_copy[pwd_field] = {
                        'data': {'query': client_config_copy[pwd_field]['query']},
                        'type': VAULT_PROVIDER
                    }
                    save_to_db = True
                # legacy thycotic format is  {'query': int}
                elif isinstance(client_config_copy[pwd_field].get('query'), int):
                    print(f'Updating Adapter:{adapter_name} Client:{client_id} '
                          f'found with legacy thycotic vault data field {pwd_field}')
                    client_config_copy[pwd_field] = {
                        'data': {'secret': client_config_copy[pwd_field]['query'],
                                 'field': 'Password'},
                        'type': VAULT_PROVIDER
                    }
                    save_to_db = True

            if save_to_db:
                self.encrypt_dict(adapter_name, client_config_copy)
                adaper_clients_collection.update_one(
                    {
                        '_id': adapter_client.get('_id')
                    },
                    {
                        '$set': {CLIENT_CONFIG: client_config_copy}
                    }
                )

        except Exception as e:
            print(f'failed to fix client config with legacy vault data format: {e}')
            traceback.print_exc()


def replace_notification_content_with_hooks(notification_content, regex):
    """
    Iterate over all found links in the notification content. For each of the links, replace it
    with hook (e.g {LINK_0}) and append a new hook item to the hooks array. Each hook item looks like
    {type: 'link', key: {LINK_0}, value: 'the actual link'}.
    :param notification_content: the notification string content.
    :param regex: the regex to match.
    :return: return hooks array and the replaced content.
    """

    hooks = []
    found_link = set()  # This is used to keep track of already found and replaced links.
    matches = re.findall(regex, notification_content)
    if matches:
        for i, link in enumerate(matches):
            if link in found_link:
                continue
            found_link.add(link)
            key = f'LINK_{i}'
            notification_content = notification_content.replace(link, f'{{{key}}}')
            link_type = {
                'type': NotificationHookType.LINK.value,
                'key': key,
                'value': link
            }
            hooks.append(link_type)
        return hooks, notification_content

    return hooks, notification_content
