import os
from pathlib import Path

ENCRYPTION_KEY_FILENAME = '.__key'
PROXY_DATA_FILE = 'proxy_data.json'  # do not modify! used in chef!
AXONIUS_SETTINGS_DIR_NAME = '.axonius_settings'
CORTEX_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..'))
AXONIUS_SETTINGS_HOST_PATH = Path(CORTEX_PATH) / AXONIUS_SETTINGS_DIR_NAME
BOOTED_FOR_PRODUCTION_MARKER_PATH = AXONIUS_SETTINGS_HOST_PATH / '.booted_for_production'
INSTANCE_CONNECT_USER_NAME = 'node_maker'  # todo: define once!
PASSWORD_GET_URL = 'https://core.axonius.local/api/node/'
DB_PASSWORD_GET_URL = 'https://core.axonius.local/api/dbpass'
ADAPTER_RESTART_COMMAND = f'sh -c "cd {CORTEX_PATH} && ./axonius.sh system up --all ' \
                          '--prod --restart --env NODE_INIT_NAME={init_name}"'
STOP_SYSTEM_COMMAND = 'sh -c "cd /home/ubuntu/cortex && ./axonius.sh system down --all"'
MASTER_ADDR_HOST_PATH = AXONIUS_SETTINGS_HOST_PATH / '__master'
ENCRYPTION_KEY_HOST_PATH = AXONIUS_SETTINGS_HOST_PATH / ENCRYPTION_KEY_FILENAME
PROXY_DATA_HOST_PATH = AXONIUS_SETTINGS_HOST_PATH / PROXY_DATA_FILE
WEAVE_NETWORK_SUBNET_KEY = 'weave-network-subnet'

VPN_DATA_DIR = Path(AXONIUS_SETTINGS_HOST_PATH) / 'vpn_data'
TUNNEL_RESOLV_FILE_HOST_PATH = VPN_DATA_DIR / 'client-side-resolv.conf'
GENERATED_RESOLV_CONF_PATH = Path(AXONIUS_SETTINGS_HOST_PATH) / 'combined-resolv.conf'
VPNNET_NETWORK = 'vpnnet'
DOCKER_NETWORK_SUBNET_KEY = 'docker-network-subnet'
DOCKER_TUNNEL_SUBNET_KEY = 'docker-vpnnet-subnet'
NOLOGINER_USER_NAME = 'nologiner'
UPGRADE_USER_NAME = 'axonius_upgrade'
INSTANCE_MODE = 'instance-mode'

UPGRADE_SCRIPT_PATH = Path(CORTEX_PATH) / 'devops/scripts/instances/run_upgrade_on_instance.sh'
