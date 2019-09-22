import shlex
import subprocess
import sys

import docker

from scripts.instances.network_utils import connect_to_master, update_weave_connection_params
from scripts.instances.instances_consts import (ADAPTER_RESTART_COMMAND,
                                                PASSWORD_GET_URL,
                                                BOOTED_FOR_PRODUCTION_MARKER_PATH,
                                                CORTEX_PATH)
from services.axonius_service import get_service
from axonius.consts.system_consts import NODE_MARKER_PATH


def shut_down_system():
    subprocess.check_call(['./axonius.sh', 'system', 'down', '--all'], cwd=CORTEX_PATH)
    print('Done shut down system')


def restart_all_adapters(init_name):
    print('Restarting all adapters')
    command = shlex.split(ADAPTER_RESTART_COMMAND.format(init_name=init_name))
    subprocess.check_call(command, cwd=CORTEX_PATH)
    print('Done restart all adapters')


def change_instance_setup_user_pass():
    axonius_service = get_service()
    node_id = ''
    for plugin_name, plugin in axonius_service.get_all_plugins():
        try:
            plugin_service = plugin()
            node_id = plugin_service.vol_conf.node_id
            if node_id:
                new_password, _, _ = \
                    plugin_service.run_command_in_container(f'curl -kfsSL {PASSWORD_GET_URL}{node_id}')
                break
        except Exception as e:
            print(f'failed to read node_id from {plugin_name} {plugin} - {e}')

    if not node_id:
        print(f'failed to read node_id from all of the running adapters')
        raise Exception('node_id not found')

    print(f'Password len is {len(new_password)}')
    subprocess.check_call(f'sudo usermod --password $(openssl passwd -1 {new_password}) node_maker',
                          shell=True)
    print('done!')


def setup_node(connection_string):
    master_ip, weave_pass, init_name = connection_string
    master_ip = master_ip.strip()
    weave_pass = weave_pass.strip()
    init_name = init_name.strip()
    shut_down_system()
    update_weave_connection_params(weave_pass, master_ip)
    connect_to_master(master_ip, weave_pass)
    NODE_MARKER_PATH.touch()
    restart_all_adapters(init_name)
    change_instance_setup_user_pass()


def logic_main():
    if BOOTED_FOR_PRODUCTION_MARKER_PATH.exists():
        res = input('Please enter connection string:')
        connection_string = res.split()
        if len(connection_string) != 3:
            print('Bad connection string! Please do not use spaces in any of the parameters.')
            sys.exit(1)
        else:
            setup_node(connection_string)
            print('Node successfully joined Axonius cluster.')
            sys.exit(0)
    else:
        print('System is not stable yet (Probably recently booted) please wait a few minutes and try again.')
        sys.exit(1)
