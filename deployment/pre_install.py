"""
This script is run *from the install.py* and saves current state data +
    system configuration (that will be loaded back to a new system using post_install.py).
"""
import argparse
from configparser import ConfigParser
from cryptography.fernet import Fernet
import json
from pymongo import MongoClient
import os
import sys

from utils import AutoOutputFlush, CORTEX_PATH, get_service, print_state


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
    state = {
        'version': current_state_file_version,
        'providers': get_all_providers(),
        'diag_env': open(os.path.join(CORTEX_PATH, 'diag_env.json'), 'r').read()
    }
    state_string = json.dumps(state, indent=2)
    enc_state_binary = encrypt(state_string, key)
    with open(path, 'wb') as f:
        f.write(enc_state_binary)


def encrypt(data, key):
    f = Fernet(key)
    return f.encrypt(data.encode('utf-8'))


def get_all_providers():
    print_state(f'  Extracting Providers')
    client = get_mongo_client()
    providers = {}
    core_configs_db = client['core']['configs']
    for adapter_config in core_configs_db.find({'plugin_type': 'Adapter'}):
        adapter_name = adapter_config['plugin_name']
        plugin_unique_name = adapter_config['plugin_unique_name']
        for provider in client[plugin_unique_name]['clients'].find():
            providers.setdefault(adapter_name, []).append(provider['client_config'])
    return providers


def get_mongo_client():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plugins', 'core', 'config.ini')
    config = ConfigParser()
    config.read(config_path)

    db_host = config['core_specific']['db_addr'].replace('mongo:', 'localhost:')
    db_user = config['core_specific']['db_user']
    db_password = config['core_specific']['db_password']
    return MongoClient(db_host, username=db_user, password=db_password)


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
