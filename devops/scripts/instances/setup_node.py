#!/usr/bin/env python3
import configparser
import os
import shlex
import subprocess
import sys
from pathlib import Path

CORTEX_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..'))
AXONIUS_SETTINGS_PATH = Path(CORTEX_PATH) / '.axonius_settings'
BOOTED_FOR_PRODUCTION_MARKER_PATH = AXONIUS_SETTINGS_PATH / '.booted_for_production'
INSTANCE_CONNECT_USER_NAME = 'node_maker'
VOLATILE_CONFIG_PATH = '/home/axonius/plugin_volatile_config.ini'
PASSWORD_GET_URL = 'https://core.axonius.local/api/node/'
ADAPTER_RESTART_COMMAND = './axonius.sh adapter all up --restart --exclude nimbul ' \
                          'diagnostics --env NODE_INIT_NAME={init_name}'


def shut_down_system():
    subprocess.check_call(['./axonius.sh', 'system', 'down', '--all'], cwd=CORTEX_PATH)


def connect_to_master(master_ip, weave_pass):
    subprocess.check_call(['weave', 'reset'])
    subprocess.check_call(['weave', 'launch', '--dns-domain=axonius.local', '--password', weave_pass])
    subprocess.check_call(['weave', 'connect', master_ip])


def restart_all_adapters(init_name):
    command = shlex.split(ADAPTER_RESTART_COMMAND.format(init_name=init_name))
    subprocess.check_call(command, cwd=CORTEX_PATH)


def run_tunnler():
    host_ip = subprocess.check_output(shlex.split('weave dns-args')).decode('utf-8')
    host_ip = [x for x in host_ip.split() if '--dns' in x][0]
    host_ip = host_ip[len('--dns='):]
    command = shlex.split(
        'docker run -d --restart=always --name tunnle alpine/socat ' +
        f'tcp-listen:9958,reuseaddr,fork,forever tcp:{host_ip}:22')

    my_env = os.environ.copy()
    my_env['DOCKER_HOST'] = 'unix:///var/run/weave/weave.sock'

    subprocess.check_call(command, env=my_env)


def change_instance_setup_user_pass():
    adapter_list = [container for container in
                    subprocess.check_output(['docker', 'ps', '--format', '\'{{.Names}}\'']).decode('utf-8').split('\n')
                    if '-adapter' in container]

    config_string = subprocess.check_output(
        ['docker', 'exec', adapter_list[0][1:-1], 'cat', VOLATILE_CONFIG_PATH]).decode('utf-8')

    config = configparser.ConfigParser()
    config.read_string(config_string)

    my_env = os.environ.copy()
    my_env['DOCKER_HOST'] = 'unix:///var/run/weave/weave.sock'

    new_password = subprocess.check_output(['docker', 'run', '--rm', 'appropriate/curl', '-kfsSL',
                                            f'{PASSWORD_GET_URL}{config["registration"]["node_id"]}'],
                                           env=my_env).decode('utf-8')
    subprocess.check_call(f'sudo usermod --password $(openssl passwd -1 {new_password}) node_maker',
                          shell=True)


def setup_node(connection_string):
    master_ip, weave_pass, init_name = connection_string

    shut_down_system()
    connect_to_master(master_ip.strip(), weave_pass.strip())
    restart_all_adapters(init_name.strip())
    change_instance_setup_user_pass()
    run_tunnler()


def main():
    if BOOTED_FOR_PRODUCTION_MARKER_PATH.exists():
        res = input('Please enter connection string:')
        connection_string = res.split()
        if len(connection_string) != 3:
            print('Bad connection string! Please do not use spaces in any of the parameters.')
        else:
            if BOOTED_FOR_PRODUCTION_MARKER_PATH.exists():
                setup_node(connection_string)
                print('Node successfully joined Axonius cluster.')
                return sys.exit(0)

    print('System is not stable yet (Probably recently booted) please wait a few minutes and try again.')

    return sys.exit(1)


if __name__ == '__main__':
    main()
