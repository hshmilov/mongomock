"""
This script is run *from the install.py* and loads old saved data +
    system configuration (that was saved using pre_install.py).
"""
import argparse
from cryptography.fernet import Fernet
import json
import os
import sys
import time

from utils import AutoOutputFlush, CORTEX_PATH, get_service, print_state


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
    state = json.loads(decrypt(open(path, 'rb').read(), key))
    supported_state_file_version = 1
    while state['version'] < supported_state_file_version:
        state = upgrade_state(state)
    axonius_system = get_service()
    axonius_system.take_process_ownership()
    load_providers(axonius_system, state['providers'])
    load_diagnostics(axonius_system, state['diag_env'])  # SHOULD BE THE LAST STEP


def decrypt(data, key):
    f = Fernet(key)
    return f.decrypt(data).decode('utf-8')


def upgrade_state(state):
    # *Stub function for future use*
    # switch on state.version and "fix" compatibility
    # set version to new version number
    # return new state object
    raise NotImplementedError()


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
            adapter_service.add_client(provider)


def load_diagnostics(axonius_system, diag_env):
    """
    Loads the diagnostics server. Note that this function is called in the last step of the installation
    since we are assuming the upgrade process can happen remotely (we assume someone is upgrading from the
    diagnostics container).
    """
    print_state('  Restoring diagnostics env')
    open(os.path.join(CORTEX_PATH, 'diag_env.json'), 'w').write(diag_env)
    diagnostics = axonius_system.get_plugin('diagnostics')
    diagnostics.take_process_ownership()
    if diagnostics.get_is_container_up():
        if not count(10):
            print_state('    *Skipping* diagnostics restart')
        else:
            print_state('    *RESTARTING* diagnostics')
            diagnostics.start(allow_restart=True, show_print=False)


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
