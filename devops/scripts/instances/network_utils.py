import os
import random
import string
import subprocess
import shlex

from axonius.consts.system_consts import NODE_MARKER_PATH, DB_KEY_PATH, DOCKERHUB_USER, WEAVE_VERSION
from conf_tools import get_customer_conf_json
from scripts.instances.instances_consts import (MASTER_ADDR_HOST_PATH,
                                                ENCRYPTION_KEY_HOST_PATH,
                                                AXONIUS_SETTINGS_HOST_PATH,
                                                WEAVE_NETWORK_SUBNET_KEY)

DEFAULT_WEAVE_SUBNET_IP_RANGE = '171.17.0.0/16'


def get_weave_subnet_ip_range():
    conf = get_customer_conf_json()

    weave_subnet = conf.get(WEAVE_NETWORK_SUBNET_KEY, DEFAULT_WEAVE_SUBNET_IP_RANGE)

    if WEAVE_NETWORK_SUBNET_KEY in conf:
        print(f'Found custom weave network ip range: {weave_subnet}')
    else:
        print(f'Using default weave ip range {weave_subnet}')

    return weave_subnet


def update_weave_connection_params(weave_encryption_key, master_ip):
    ENCRYPTION_KEY_HOST_PATH.write_text(weave_encryption_key)
    MASTER_ADDR_HOST_PATH.write_text(master_ip)
    print('Done update weave connection params')


def update_db_enc_key(db_encryption_key):
    DB_KEY_PATH.write_text(db_encryption_key)
    print('Done update DB encryption key')


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


def connect_to_master(master_ip, weave_pass):
    print('Connecting to master')
    subnet_ip_range = get_weave_subnet_ip_range()
    subprocess.check_call(shlex.split(f'weave reset --force'))
    my_env = os.environ.copy()
    my_env['DOCKERHUB_USER'] = DOCKERHUB_USER
    my_env['WEAVE_VERSION'] = WEAVE_VERSION
    subprocess.check_call(shlex.split(
        f'weave launch --dns-domain=axonius.local --ipalloc-range {subnet_ip_range} --password {weave_pass}'),
        env=my_env)
    subprocess.check_call(shlex.split(f'weave connect {master_ip}'))
    print('Done weave connect')
    run_tunnler()
    print('Done run tunnler')
    run_proxy_socat()
    print('Done connecting to master')


def get_encryption_key():
    if ENCRYPTION_KEY_HOST_PATH.is_file():
        return ENCRYPTION_KEY_HOST_PATH.read_text()
    else:
        # Creating a new one if it doesn't exist yet.
        encryption_key = ''.join(random.SystemRandom().choices(string.ascii_uppercase +
                                                               string.ascii_lowercase + string.digits, k=32))

        AXONIUS_SETTINGS_HOST_PATH.mkdir(exist_ok=True)
        ENCRYPTION_KEY_HOST_PATH.write_text(encryption_key)
        ENCRYPTION_KEY_HOST_PATH.chmod(0o646)
        return encryption_key


def restore_master_connection():
    master_ip = ''
    weave_pass = ''
    if MASTER_ADDR_HOST_PATH.is_file():
        master_ip = MASTER_ADDR_HOST_PATH.read_text()
    else:
        print(f'master file is not present')

    if ENCRYPTION_KEY_HOST_PATH.is_file():
        weave_pass = ENCRYPTION_KEY_HOST_PATH.read_text()
    else:
        print(f'weave password file is not present')

    if weave_pass and master_ip and NODE_MARKER_PATH.is_file():
        print(f'reconnecting this node to master at {master_ip}')
        connect_to_master(master_ip, weave_pass)
    else:
        print('skipping restore master connection step')
