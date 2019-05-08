import os
import shlex
import subprocess
import sys

import docker

from scripts.instances.instances_consts import (ADAPTER_RESTART_COMMAND,
                                                ENCRYPTION_KEY_HOST_PATH,
                                                MASTER_ADDR_HOST_PATH,
                                                PASSWORD_GET_URL,
                                                BOOTED_FOR_PRODUCTION_MARKER_PATH,
                                                CORTEX_PATH)
from services.axonius_service import get_service
from axonius.consts.system_consts import NODE_MARKER_PATH


def shut_down_system():
    subprocess.check_call(['./axonius.sh', 'system', 'down', '--all'], cwd=CORTEX_PATH)


def connect_to_master(master_ip, weave_pass):
    subprocess.check_call(['weave', 'reset'])
    subprocess.check_call(
        ['weave', 'launch', '--dns-domain=axonius.local', '--ipalloc-range', '171.17.0.0/16', '--password', weave_pass])
    subprocess.check_call(['weave', 'connect', master_ip])


def restart_all_adapters(init_name):
    command = shlex.split(ADAPTER_RESTART_COMMAND.format(init_name=init_name))
    subprocess.check_call(command, cwd=CORTEX_PATH)


def run_tunnler():
    # TODO: rewrite using docker lib (and the proxy one)
    host_ip = subprocess.check_output(shlex.split('weave dns-args')).decode('utf-8')
    host_ip = [x for x in host_ip.split() if '--dns' in x][0]
    host_ip = host_ip[len('--dns='):]
    container_name = 'tunnler'
    command = shlex.split(
        f'docker run -d --restart=always --name {container_name} alpine/socat ' +
        f'tcp-listen:9958,reuseaddr,fork,forever tcp:{host_ip}:22')

    my_env = os.environ.copy()
    my_env['DOCKER_HOST'] = 'unix:///var/run/weave/weave.sock'

    # Removing old container if exists (If this script is being run to reconnect an existing node).
    subprocess.call(shlex.split(f'docker rm -f {container_name}'))
    subprocess.check_call(command, env=my_env)


def run_proxy_socat():
    container_name = 'proxy-socat'
    proxy_dns = 'master-proxy.axonius.local'
    proxy_port = 8888
    command = shlex.split(
        f'docker run -d --restart=always '
        f'--publish 127.0.0.1:{proxy_port}:{proxy_port} '
        f'--name {container_name} alpine/socat '
        f'tcp-listen:{proxy_port},reuseaddr,fork,forever tcp:{proxy_dns}:{proxy_port}')

    my_env = os.environ.copy()
    my_env['DOCKER_HOST'] = 'unix:///var/run/weave/weave.sock'

    # Removing old tunnler if exists (If this script is being run to reconnect an existing node).
    subprocess.call(shlex.split(f'docker rm -f {container_name}'))
    subprocess.check_call(command, env=my_env)


def change_instance_setup_user_pass():
    axonius_service = get_service()
    node_id = ''
    for adapter_name, adapter in axonius_service.get_all_adapters():
        try:
            adapter_service = adapter()
            node_id = adapter_service.vol_conf.node_id
            if node_id:
                break
        except Exception as e:
            print(f'failed to read node_id from {adapter_name} {adapter} - {e}')

    if not node_id:
        print(f'failed to read node_id from all of the running adapters')
        raise Exception('node_id not found')

    client = docker.from_env(environment={'DOCKER_HOST': 'unix:///var/run/weave/weave.sock'})
    new_password = client.containers.run('appropriate/curl', auto_remove=True,
                                         command=f'-kfsSL {PASSWORD_GET_URL}{node_id}').decode('utf-8')

    subprocess.check_call(f'sudo usermod --password $(openssl passwd -1 {new_password}) node_maker',
                          shell=True)


def update_weave_connection_params(weave_encryption_key, master_ip):
    ENCRYPTION_KEY_HOST_PATH.write_text(weave_encryption_key)
    MASTER_ADDR_HOST_PATH.write_text(master_ip)


def setup_node(connection_string):
    master_ip, weave_pass, init_name = connection_string
    master_ip = master_ip.strip()
    weave_pass = weave_pass.strip()
    init_name = init_name.strip()

    shut_down_system()
    update_weave_connection_params(weave_pass, master_ip)
    connect_to_master(master_ip, weave_pass)
    run_tunnler()
    run_proxy_socat()
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
