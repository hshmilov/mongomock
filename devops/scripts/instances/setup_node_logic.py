import os
import shlex
import subprocess
import sys

from scripts.instances.instances_modes import InstancesModes, get_instance_mode
from scripts.instances.network_utils import connect_to_master, update_weave_connection_params, update_db_enc_key
from scripts.instances.instances_consts import (ADAPTER_RESTART_COMMAND,
                                                PASSWORD_GET_URL,
                                                DB_PASSWORD_GET_URL,
                                                BOOTED_FOR_PRODUCTION_MARKER_PATH,
                                                CORTEX_PATH)
from services.axonius_service import get_service
from axonius.consts.system_consts import NODE_MARKER_PATH, DOCKERHUB_URL, USING_WEAVE_PATH
from services.plugins.instance_control_service import InstanceControlService


def shut_down_system():
    command = 'sudo /sbin/runuser -l ubuntu -c "cd /home/ubuntu/cortex && ./axonius.sh system down --all"'
    subprocess.check_call(shlex.split(command))
    print('Done shut down system')


def restart_all_adapters(init_name):
    print('Restarting all adapters')
    command = shlex.split(ADAPTER_RESTART_COMMAND.format(init_name=init_name))
    subprocess.check_call(command, cwd=CORTEX_PATH)
    print('Done restart all adapters')


def change_instance_setup_user_pass():
    axonius_service = get_service()
    node_id = ''
    all_plugins = axonius_service.get_all_plugins()
    # add instance control plugin for nodes running mongo only
    all_plugins.append((axonius_service.instance_control.plugin_name, InstanceControlService))
    for plugin_name, plugin in all_plugins:
        try:
            plugin_service = plugin()
            node_id = plugin_service.vol_conf.node_id
            if node_id:
                new_password, _, _ = \
                    plugin_service.run_command_in_container(f'curl -kfsSL {PASSWORD_GET_URL}{node_id}')
                new_password = new_password.decode('ascii')
                break
        except Exception as e:
            print(f'failed to read node_id from {plugin_name} {plugin} - {e}')

    if not node_id:
        print(f'failed to read node_id from all of the running adapters')
        raise Exception('node_id not found')

    print(f'Password len is {len(new_password)}, "{new_password[:4]}..."')
    subprocess.check_call(f'sudo /usr/sbin/usermod --password $(openssl passwd -1 {new_password}) node_maker',
                          shell=True)
    print('done!')


def get_db_pass_from_core() -> str:
    """
    Get db password from core using curl docker container inside weave network
    Notes: using 'docker' library is best practice, but it sometimes returns empty values on container run.
    :return: base64 encoded password
    """
    try:
        my_env = os.environ.copy()
        my_env['DOCKER_HOST'] = 'unix:///var/run/weave/weave.sock'
        command = f'docker run --rm {DOCKERHUB_URL}appropriate/curl -kfsSL {DB_PASSWORD_GET_URL}'
        password = subprocess.check_output(shlex.split(command), env=my_env).decode('ascii')
        if not password:
            print('Error getting db pass')
        return password
    except Exception:
        print('Exception while getting db pass')


def setup_node(connection_string):
    master_ip, weave_pass, init_name = connection_string
    master_ip = master_ip.strip()
    weave_pass = weave_pass.strip()
    init_name = init_name.strip()
    shut_down_system()
    update_weave_connection_params(weave_pass, master_ip)
    USING_WEAVE_PATH.touch()
    connect_to_master(master_ip, weave_pass)
    NODE_MARKER_PATH.touch()
    # on a node with only mongo, we don't need the db pass,
    # which is used today only as an env-variable for plugins that need to interact with mongo.
    if get_instance_mode() != InstancesModes.mongo_only.value:
        db_pass = get_db_pass_from_core()
        update_db_enc_key(db_pass)
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
