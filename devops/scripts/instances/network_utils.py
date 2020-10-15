import random
import string
import subprocess
import shlex
from pathlib import Path

from axonius.consts.plugin_consts import CORE_UNIQUE_NAME, MONGO_UNIQUE_NAME, AXONIUS_MANAGER_PLUGIN_NAME
from axonius.consts.system_consts import NODE_MARKER_PATH, DB_KEY_PATH, WEAVE_PATH
from conf_tools import get_customer_conf_json
from install_utils import get_weave_subnet_ip_range
from scripts.instances.instances_consts import (MASTER_ADDR_HOST_PATH,
                                                ENCRYPTION_KEY_HOST_PATH,
                                                AXONIUS_SETTINGS_HOST_PATH,
                                                WEAVE_NETWORK_SUBNET_KEY,
                                                DOCKER_NETWORK_SUBNET_KEY, DOCKER_TUNNEL_SUBNET_KEY)
from services.standalone_services.tunneler_service import TunnelerService
from services.standalone_services.node_proxy_service import NodeProxyService
DEFAULT_DOCKER_SUBNET_IP_RANGE = '172.18.254.0/24'
DEFAULT_WEAVE_SUBNET_IP_RANGE = '171.17.0.0/16'
DEFAULT_DOCKER_TUNNEL_SUBNET_IP_RANGE = '171.18.0.0/16'
DOCKER_NETOWRK_DEFAULT_DNS = '172.17.0.1'
DOCKER_TUNNEL_INTERFACE_NAME = 'br-ax-vpnnet'
DOCKER_BRIDGE_INTERFACE_NAME = 'br-ax-docker'
DOCKER_BRIDGE_INSPECT_COMMAND = "docker network inspect bridge --format='{{(index .IPAM.Config 0).Gateway}}'"


def get_docker_subnet_ip_range():
    conf = get_customer_conf_json()

    docker_subnet = conf.get(DOCKER_NETWORK_SUBNET_KEY, DEFAULT_DOCKER_SUBNET_IP_RANGE)

    if DOCKER_NETWORK_SUBNET_KEY in conf:
        print(f'Found custom docker network ip range: {docker_subnet}')
    else:
        print(f'Using default docker ip range {docker_subnet}')

    return docker_subnet


def get_tunnel_subnet_ip_rage():
    conf = get_customer_conf_json()
    vpnnet_subnet = conf.get(DOCKER_TUNNEL_SUBNET_KEY, DEFAULT_DOCKER_TUNNEL_SUBNET_IP_RANGE)

    if DOCKER_TUNNEL_SUBNET_KEY in conf:
        print(f'Found custom VPN network ip range: {vpnnet_subnet}')
    else:
        print(f'Using default VPN ip range {vpnnet_subnet}')

    return vpnnet_subnet


def get_docker_bridge_default_gateway():
    ip = DOCKER_NETOWRK_DEFAULT_DNS
    try:
        ip = subprocess.check_output(shlex.split(DOCKER_BRIDGE_INSPECT_COMMAND)).decode('utf-8').strip()
        if not ip:
            print('empty response from docker inspect command')
            ip = DOCKER_NETOWRK_DEFAULT_DNS
    except Exception as e:
        print(f'error getting docker bridge default gateway {e}, using {ip}')
    return ip


def update_weave_connection_params(weave_encryption_key, master_ip):
    ENCRYPTION_KEY_HOST_PATH.write_text(weave_encryption_key)
    MASTER_ADDR_HOST_PATH.write_text(master_ip)
    print('Done update weave connection params')


def update_db_enc_key(db_encryption_key):
    DB_KEY_PATH.write_text(db_encryption_key)
    print('Done update DB encryption key')


def run_tunneler():
    tunneler_service = TunnelerService()
    tunneler_service.take_process_ownership()
    tunneler_service.start(allow_restart=True, show_print=False, mode='prod')


def run_proxy_socat():
    tunneler_service = NodeProxyService()
    tunneler_service.take_process_ownership()
    tunneler_service.start(allow_restart=True, show_print=False, mode='prod')


def connect_axonius_manager_to_weave():
    weave_attach_command = shlex.split(f'{WEAVE_PATH} attach {AXONIUS_MANAGER_PLUGIN_NAME}')
    subprocess.check_call(weave_attach_command)


def weave_dns_lookup(hostname: str) -> str:
    command = shlex.split(f'weave dns-lookup {hostname}')
    return subprocess.check_output(command).decode('utf-8').splitlines()[0]


def fix_node_axonius_manager_hosts():
    connect_axonius_manager_to_weave()
    hosts_file = Path('/etc/hosts')
    hosts_data = hosts_file.read_text()
    if CORE_UNIQUE_NAME in hosts_data:
        return
    core_ip = weave_dns_lookup(CORE_UNIQUE_NAME)
    mongo_ip = weave_dns_lookup(MONGO_UNIQUE_NAME)
    hosts_data = f'{hosts_data}{core_ip}\t{CORE_UNIQUE_NAME}\n{mongo_ip}\t{MONGO_UNIQUE_NAME}\n'
    hosts_file.write_text(hosts_data)


def connect_to_master(master_ip, weave_pass):
    print('Connecting to master')
    subnet_ip_range = get_weave_subnet_ip_range()
    subprocess.check_call(shlex.split(f'weave reset --force'))
    subprocess.check_call(shlex.split(
        f'weave launch --dns-domain=axonius.local --ipalloc-range {subnet_ip_range} --password {weave_pass}'))
    subprocess.check_call(shlex.split(f'weave connect {master_ip}'))
    print('Done weave connect')
    run_tunneler()
    print('Done run tunneler')
    run_proxy_socat()
    print('Done connecting to master')


def get_encryption_key():
    if ENCRYPTION_KEY_HOST_PATH.is_file():
        return ENCRYPTION_KEY_HOST_PATH.read_text()

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
