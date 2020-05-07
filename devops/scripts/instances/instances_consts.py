import os
from pathlib import Path

from axonius.consts.gui_consts import ENCRYPTION_KEY_FILENAME, PROXY_DATA_FILE
from axonius.consts.plugin_consts import AXONIUS_SETTINGS_DIR_NAME

CORTEX_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..'))
AXONIUS_SETTINGS_HOST_PATH = Path(CORTEX_PATH) / AXONIUS_SETTINGS_DIR_NAME
BOOTED_FOR_PRODUCTION_MARKER_PATH = AXONIUS_SETTINGS_HOST_PATH / '.booted_for_production'
INSTANCE_CONNECT_USER_NAME = 'node_maker'  # todo: define once!
PASSWORD_GET_URL = 'https://core.axonius.local/api/node/'
DB_PASSWORD_GET_URL = 'https://core.axonius.local/api/dbpass'
ADAPTER_RESTART_COMMAND = f'sudo /sbin/runuser -l ubuntu -c "cd {CORTEX_PATH} && ./axonius.sh system up --all ' \
                          '--prod --restart --env NODE_INIT_NAME={init_name}"'
MASTER_ADDR_HOST_PATH = AXONIUS_SETTINGS_HOST_PATH / '__master'
ENCRYPTION_KEY_HOST_PATH = AXONIUS_SETTINGS_HOST_PATH / ENCRYPTION_KEY_FILENAME
PROXY_DATA_HOST_PATH = AXONIUS_SETTINGS_HOST_PATH / PROXY_DATA_FILE
WEAVE_NETWORK_SUBNET_KEY = 'weave-network-subnet'
DOCKER_NETWORK_SUBNET_KEY = 'docker-network-subnet'
