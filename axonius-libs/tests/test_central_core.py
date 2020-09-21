import datetime
import logging
import sys
import uuid

import mongomock

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG
from axonius.consts.plugin_consts import PLUGIN_NAME, AGGREGATOR_PLUGIN_NAME, DEVICES_DB, USERS_DB
from axonius.entities import EntityType
from axonius.modules.central_core import CentralCore
from axonius.modules.plugin_settings import Consts as PluginSettingsConsts
from axonius.utils.hash import get_preferred_quick_adapter_id


def generate_some_entity(plugin_name: str, _id: str) -> dict:
    now = datetime.datetime.now()
    return {
        'internal_axon_id': '1-' + uuid.uuid4().hex,
        'accurate_for_datetime': now,
        'adapters': [
            {
                'client_used': 'SomeClient',
                'plugin_type': 'Adapter',
                'plugin_name': plugin_name,
                'plugin_unique_name': f'{plugin_name}_0',
                'accurate_for_datetime': now,
                'quick_id': get_preferred_quick_adapter_id(f'{plugin_name}_0', _id),
                'data': {
                    'id': _id,
                    'raw': {
                    },
                }
            }
        ],
        'tags': []
    }


def get_mongo_client() -> mongomock.MongoClient:
    db = mongomock.MongoClient()
    db['core'][PluginSettingsConsts.AllConfigurableConfigs].insert_one({
        PLUGIN_NAME: 'gui',
        PluginSettingsConsts.ConfigName: FEATURE_FLAGS_CONFIG,
        PluginSettingsConsts.Config: {
            'trial_end': '',
            'expiry_date': '',
            'lock_on_expiry': False,
            'locked_actions': [],
            'bandicoot': False,
            'bandicoot_result_compare_only': False,
            'experimental_api': False,
            'cloud_compliance': {'enabled': False, 'cis_enabled': False, 'expiry_date': ''},
            'root_master_settings': {'enabled': True, 'delete_backups': False},
            'parallel_search': {'enabled': False},
            'reenter_credentials': False,
            'refetch_action': False,
            'enable_fips': False,
            'disable_rsa': False,
            'higher_ciphers': False,
            'enable_saas': False,
            'query_timeline_range': False,
            'enforcement_center': True,
            'do_not_use_software_name_and_version_field': False,
            'do_not_populate_heavy_fields': False,
            'dashboard_control': {'present_call_limit': 10, 'historical_call_limit': 5}
        }
    })

    return db


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    db = get_mongo_client()
    aggregator = db[AGGREGATOR_PLUGIN_NAME]
    central_core = CentralCore(db)

    # If the indexes have been created then this collection would be there
    assert 'central_core_devices_db' in aggregator.collection_names()

    # Put something in there
    aggregator[DEVICES_DB].insert_one(generate_some_entity('aws_adapter', 'i-1'))
    aggregator[USERS_DB].insert_one(generate_some_entity('aws_adapter', 'u-1'))

    # assert they are there
    assert aggregator[DEVICES_DB].find_one({'adapters.data.id': 'i-1'})
    assert aggregator[USERS_DB].find_one({'adapters.data.id': 'u-1'})

    # put some other devices into the central core db
    central_core.entity_db_map[EntityType.Devices].insert_one(generate_some_entity('aws_adapter', 'i-2'))
    central_core.entity_db_map[EntityType.Users].insert_one(generate_some_entity('aws_adapter', 'u-2'))

    # Promote it
    central_core.promote_central_core()

    now_collection_names = aggregator.collection_names()
    for collection_name in [
            'devices_db', 'users_db', 'device_adapters_raw_db', 'user_adapters_raw_db', 'central_core_users_db',
            'central_core_devices_db', 'central_core_user_adapters_raw_db', 'central_core_device_adapters_raw_db'
    ]:
        assert collection_name in now_collection_names

    # assert new collections are empty
    assert len(list(central_core.entity_db_map[EntityType.Devices].find({}))) == 0
    assert len(list(central_core.entity_db_map[EntityType.Users].find({}))) == 0

    # assert the devices and users have been moved to the new collection name
    assert aggregator[DEVICES_DB].find_one({'adapters.data.id': 'i-2'})
    assert aggregator[USERS_DB].find_one({'adapters.data.id': 'u-2'})


if __name__ == '__main__':
    sys.exit(main())
