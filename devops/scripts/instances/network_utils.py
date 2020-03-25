import os
import random
import string
import subprocess
import shlex

from axonius.consts.system_consts import NODE_MARKER_PATH, DB_KEY_PATH, DOCKERHUB_URL
from conf_tools import get_customer_conf_json
from scripts.instances.instances_consts import (MASTER_ADDR_HOST_PATH,
                                                ENCRYPTION_KEY_HOST_PATH,
                                                AXONIUS_SETTINGS_HOST_PATH,
                                                WEAVE_NETWORK_SUBNET_KEY)
from services.standalone_services.tunneler_service import TunnelerService
from services.standalone_services.node_proxy_service import NodeProxyService

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


def run_tunneler():
    tunneler_service = TunnelerService()
    tunneler_service.take_process_ownership()
    tunneler_service.start(allow_restart=True, show_print=False, mode='prod')


def run_proxy_socat():
    tunneler_service = NodeProxyService()
    tunneler_service.take_process_ownership()
    tunneler_service.start(allow_restart=True, show_print=False, mode='prod')


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
