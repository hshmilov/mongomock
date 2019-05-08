import os
from pathlib import Path

from axonius.consts.plugin_consts import AXONIUS_SETTINGS_DIR_NAME

####################################################################################################################
# These consts include paths that are only relevant on the host machine (outside of the docker container context). #
####################################################################################################################


# Sadly we are very far from cortex.
CORTEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')

METADATA_PATH = os.path.join(CORTEX_PATH, 'shared_readonly_files', '__build_metadata')
SYSTEM_CONF_PATH = Path(CORTEX_PATH) / 'system_conf.json'
CUSTOMER_CONF_RELATIVE_PATH = Path(AXONIUS_SETTINGS_DIR_NAME) / 'customer_conf.json'
NODE_CONF_PATH = Path(CORTEX_PATH) / 'node_conf.json'
CUSTOMER_CONF_PATH = Path(CORTEX_PATH) / CUSTOMER_CONF_RELATIVE_PATH
AXONIUS_MOCK_DEMO_ENV_VAR = 'AXONIUS_MOCK_MODE=TRUE'
CONNECTED_TO_MASTER_FILE = 'connected_to_master.marker'
NODE_MARKER_RELATIVE_PATH = Path(AXONIUS_SETTINGS_DIR_NAME) / CONNECTED_TO_MASTER_FILE
NODE_MARKER_PATH = Path(CORTEX_PATH) / NODE_MARKER_RELATIVE_PATH


AXONIUS_NETWORK = 'axonius'
WEAVE_NETWORK = 'axonius-weave'
AXONIUS_DNS_SUFFIX = 'axonius.local'
WEAVE_PATH = '/usr/local/bin/weave'
