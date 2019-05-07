import os
from pathlib import Path

from axonius.consts.gui_consts import ENCRYPTION_KEY_FILENAME
from axonius.consts.plugin_consts import AXONIUS_SETTINGS_DIR_NAME

CORTEX_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..'))
AXONIUS_SETTINGS_PATH = Path(CORTEX_PATH) / AXONIUS_SETTINGS_DIR_NAME
BOOTED_FOR_PRODUCTION_MARKER_PATH = AXONIUS_SETTINGS_PATH / '.booted_for_production'
INSTANCE_CONNECT_USER_NAME = 'node_maker'  # todo: define once!
PASSWORD_GET_URL = 'https://core.axonius.local/api/node/'
ADAPTER_RESTART_COMMAND = './axonius.sh system up --all --prod --restart --env NODE_INIT_NAME={init_name}'
MASTER_ADDR_HOST_PATH = AXONIUS_SETTINGS_PATH / '__master'
ENCRYPTION_KEY_HOST_PATH = AXONIUS_SETTINGS_PATH / ENCRYPTION_KEY_FILENAME
