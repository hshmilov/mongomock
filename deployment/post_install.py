"""
This script is run *from the install.py* and loads old saved data +
    system configuration (that was saved using pre_install.py).
"""
import argparse
from cryptography.fernet import Fernet
import os
import sys
import time

from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS
from axonius.devices import deep_merge_only_dict
from utils import AutoOutputFlush, CORTEX_PATH, get_service, print_state, get_mongo_client
from axonius.utils.json import from_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', '-f', required=True)
    parser.add_argument('--key', '-k', required=True)

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    load_state(args.file, args.key)


def load_state(path, key):
    print_state(f'Loading state from {path}')
    if not os.path.isfile(path):
        print_state('  File not found - skipping')
        return
    state = from_json(decrypt(open(path, 'rb').read(), key))
    supported_state_file_version = 1

    while state['version'] < supported_state_file_version:
        state = upgrade_state(state)

    axonius_system = get_service()
    mongo_client = get_mongo_client()
    axonius_system.take_process_ownership()
    load_providers(axonius_system, state['providers'])
    load_queries(axonius_system, mongo_client, state['queries'])
    load_views(axonius_system, mongo_client, state['views'])
    load_dashboard_panels(axonius_system, mongo_client, state['panels'])
    load_alerts(axonius_system, mongo_client, state['alerts'])


def decrypt(data, key):
    f = Fernet(key)
    return f.decrypt(data).decode('utf-8')


def upgrade_state(state):
    # *Stub function for future use*
    # switch on state.version and "fix" compatibility
    # set version to new version number
    # return new state object
    raise NotImplementedError()


def load_all_plugin_configs(mongo_client, configs_state):
    print_state('  Restoring configs:')
    for plugin, settings in configs_state.items():
        try:
            saved_config = configs_state[plugin]
            config_collection = mongo_client[plugin][CONFIGURABLE_CONFIGS]

            def_config = list(config_collection.find(projection={'_id': 0}))
            for def_item in def_config:
                def_name = def_item['config_name']
                def_config_content = def_item['config']
                for saved_item in saved_config:
                    saved_name = saved_item['config_name']
                    saved_config_content = saved_item['config']

                    if def_name == saved_name:
                        deep_merge_only_dict(saved_config_content, def_config_content)

            config_collection.remove({})
            config_collection.insert_many(def_config)
        except Exception as e:
            print(f'Failed to load current config of {plugin} - {e}')


def load_providers(axonius_system, adapters_providers):
    print_state('  Restoring providers for adapters:')
    all_adapters = [service_class() for module_name, service_class in axonius_system.get_all_adapters()]
    adapters_by_name = dict([(service.plugin_name, service) for service in all_adapters])
    for adapter_name, providers in adapters_providers.items():
        adapter_service = adapters_by_name.get(adapter_name)
        if adapter_service is None:
            print(f'  - {adapter_name} - not found... (skipped)')
            continue
        print(f'  - {adapter_name}')
        for provider in providers:
            try:
                adapter_service.add_client(provider)
            except Exception as e:
                print(f"Failed adding client to {str(provider)}. Got the following exception {str(e)}")


def load_queries(axonius_system, mongo, queries):
    if not queries:
        return
    print_state('  Restoring queries')
    for query_table, query_list in queries.items():
        try:
            collection = mongo[axonius_system.gui.unique_name][query_table]
            collection.remove({})
            if query_list:
                collection.insert_many(query_list)
        except Exception as e:
            print(f"Failed loading query, got the following exception {str(e)}")


def load_views(axonius_system, mongo, views):
    if not views:
        return
    print_state('  Restoring views')
    for view_table, view_list in views.items():
        try:
            collection = mongo[axonius_system.gui.unique_name][view_table]
            collection.remove({})
            if view_list:
                collection.insert_many(view_list)
        except Exception as e:
            print(f"Failed loading view. Got the following exception: {str(e)}")


def load_dashboard_panels(axonius_system, mongo, panels):
    if not panels:
        return
    print_state('  Restoring dashboard panels')
    try:
        collection = mongo[axonius_system.gui.unique_name]['dashboard']
        collection.remove({})
        if panels:
            collection.insert_many(panels)
    except Exception as e:
        print(f"Failed loading dashboard pannels, got the following exception: {str(e)}")


def load_alerts(axonius_system, mongo, alerts):
    if not alerts:
        return
    print_state('  Restoring alerts')
    try:
        collection = mongo[axonius_system.reports.unique_name]['reports']
        collection.remove({})
        if alerts:
            collection.insert_many(alerts)
    except Exception as e:
        print(f"Failed loading alerts, got the following exception: {str(e)}")


def count(x):
    try:
        for i in range(x):
            print(f'Restarting diagnostics in {x - i} seconds...' + ' ' * (len(str(x)) + 1) + '\r', end='')
            time.sleep(1)
    except KeyboardInterrupt:
        return False
    finally:
        print('\r' + ' ' * 45 + '\r')
    return True


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
