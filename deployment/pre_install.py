"""
This script is run *from the install.py* and saves current state data +
    system configuration (that will be loaded back to a new system using post_install.py).
"""
import argparse
from cryptography.fernet import Fernet
import os
import sys

from axonius.consts import plugin_consts
from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS
from utils import AutoOutputFlush, CORTEX_PATH, get_service, print_state, get_mongo_client
from axonius.utils.json import to_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', '-o', required=True)

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    key = generate_key()
    sys.stderr.write(key + '\n')  # we use stderr to communicate to our parent process
    print_loaded()
    save_state(args.out, key)


def generate_key():
    """ Generates temporary encryption key for saving and loading current system state """
    return Fernet.generate_key().decode('ascii')


def print_loaded():
    axonius_system = get_service()
    # Prepare a list of the current system components that are up; once the set up is ready, we use this list
    # to run *only* those components again after an upgrade.
    # [we use stderr to communicate to our parent process]
    sys.stderr.write('|'.join([name for name, plugin in axonius_system.get_all_plugins()
                               if plugin().get_is_container_up()]) + '\n')
    sys.stderr.write('|'.join([name for name, plugin in axonius_system.get_all_adapters()
                               if plugin().get_is_container_up()]) + '\n')


def save_state(path, key):
    print_state(f'Saving state to {path}')
    current_state_file_version = 1
    mongo_client = get_mongo_client()
    axonius_system = get_service()
    state = {
        'version': current_state_file_version,
        'providers': get_all_providers(mongo_client),
        'queries': get_all_queries(axonius_system, mongo_client),
        'views': get_all_views(axonius_system, mongo_client),
        'panels': get_dashboard_panels(axonius_system, mongo_client),
        'alerts': get_alerts(axonius_system, mongo_client),
        'config_settings': get_all_plugin_configs(mongo_client)
    }

    state_string = to_json(state, indent=2)
    enc_state_binary = encrypt(state_string, key)
    with open(path, 'wb') as f:
        f.write(enc_state_binary)


def encrypt(data, key):
    f = Fernet(key)
    return f.encrypt(data.encode('utf-8'))


def get_all_providers(mongo):
    print_state(f'  Extracting providers')
    providers = {}
    core_configs_db = mongo['core']['configs']
    for adapter_config in core_configs_db.find({'plugin_type': 'Adapter'}):
        adapter_name = adapter_config['plugin_name']
        plugin_unique_name = adapter_config['plugin_unique_name']
        for provider in mongo[plugin_unique_name]['clients'].find():
            providers.setdefault(adapter_name, []).append(provider['client_config'])
    return providers


def get_all_plugin_configs(mongo):
    print_state(f'  Extracting configs')
    all_plugins = [plugin_data[plugin_consts.PLUGIN_UNIQUE_NAME] for plugin_data in mongo['core']['configs'].find()]
    all_plugins += ['core']
    settings = {}
    for plugin in all_plugins:
        try:
            plugin_db = mongo[plugin]
            if CONFIGURABLE_CONFIGS in plugin_db.collection_names():
                settings[plugin] = list(plugin_db[CONFIGURABLE_CONFIGS].find(projection={'_id': 0}))
        except Exception as e:
            print(f'Failed to save config of {plugin}, {e}')
    return settings


def get_all_queries(axonius_system, mongo):
    print_state(f'  Extracting queries')
    return {
        'device_queries': list(mongo[axonius_system.gui.unique_name]['device_queries'].find(projection={'_id': 0})),
        'user_queries': list(mongo[axonius_system.gui.unique_name]['user_queries'].find(projection={'_id': 0}))}


def get_all_views(axonius_system, mongo):
    print_state(f'  Extracting views')
    return {'device_views': list(mongo[axonius_system.gui.unique_name]['device_views'].find(projection={'_id': 0})),
            'user_views': list(mongo[axonius_system.gui.unique_name]['user_views'].find(projection={'_id': 0}))}


def get_dashboard_panels(axonius_system, mongo):
    print_state(f'  Extracting dashboard panels')
    return list(mongo[axonius_system.gui.unique_name]['dashboard'].find(projection={'_id': 0}))


def get_alerts(axonius_system, mongo):
    print_state(f'  Extracting alerts')
    # we discard 'result' (its data is invalid since we create a new DB)
    # the report service will fetch the query and save it as the base line (under result) in the first run.
    return list(mongo[axonius_system.reports.unique_name]['reports'].find(projection={'_id': 0, 'result': 0}))


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
