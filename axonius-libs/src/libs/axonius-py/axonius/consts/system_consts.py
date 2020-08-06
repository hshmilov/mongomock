import os
from pathlib import Path

from axonius.consts.plugin_consts import AXONIUS_SETTINGS_DIR_NAME

####################################################################################################################
# These consts include paths that are only relevant on the host machine (outside of the docker container context). #
####################################################################################################################


# Sadly we are very far from cortex.
CORTEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')
PYRUN_PATH_HOST = Path(CORTEX_PATH) / 'pyrun.sh'
LOGS_PATH_HOST = Path(CORTEX_PATH) / 'logs'

METADATA_PATH = os.path.join(CORTEX_PATH, 'shared_readonly_files', '__build_metadata')
NODE_ID_ABSOLUTE_PATH = Path(CORTEX_PATH, Path(AXONIUS_SETTINGS_DIR_NAME), '.node_id')
SYSTEM_CONF_PATH = Path(CORTEX_PATH) / 'system_conf.json'
CUSTOMER_CONF_RELATIVE_PATH = Path(AXONIUS_SETTINGS_DIR_NAME) / 'customer_conf.json'
NODE_CONF_PATH = Path(CORTEX_PATH) / 'node_conf.json'
CUSTOMER_CONF_PATH = Path(CORTEX_PATH) / CUSTOMER_CONF_RELATIVE_PATH
AXONIUS_MOCK_DEMO_ENV_VAR = 'AXONIUS_MOCK_MODE=TRUE'
AXONIUS_SAAS_VAR_NAME = 'AXONIUS_SAAS_MODE'
CONNECTED_TO_MASTER_FILE = 'connected_to_master.marker'
AXONIUS_SETTINGS_PATH = Path(CORTEX_PATH, Path(AXONIUS_SETTINGS_DIR_NAME))
AXONIUS_VPN_DATA_PATH = Path(AXONIUS_SETTINGS_PATH) / 'vpn_data'
USING_WEAVE_FILE = 'using_weave.marker'
USING_WEAVE_RELATIVE_PATH = Path(AXONIUS_SETTINGS_DIR_NAME) / USING_WEAVE_FILE
USING_WEAVE_PATH = Path(CORTEX_PATH) / USING_WEAVE_RELATIVE_PATH
NODE_MARKER_RELATIVE_PATH = Path(AXONIUS_SETTINGS_DIR_NAME) / CONNECTED_TO_MASTER_FILE
NODE_MARKER_PATH = Path(CORTEX_PATH) / NODE_MARKER_RELATIVE_PATH
DB_KEY_RELATIVE_PATH = Path(AXONIUS_SETTINGS_DIR_NAME) / '.db_key'
DB_KEY_PATH = Path(CORTEX_PATH) / DB_KEY_RELATIVE_PATH
VPN_DATA_DIR_FROM_GUI = os.path.join(os.getcwd(), '..', AXONIUS_SETTINGS_DIR_NAME, 'vpn_data')
GENERIC_ERROR_MESSAGE = 'An error occurred. Please contact Axonius support. AX-ID: {}'

AXONIUS_NETWORK = 'axonius'
TUNNEL_NETWORK = 'vpnnet'
WEAVE_NETWORK = 'axonius-weave'
AXONIUS_DNS_SUFFIX = 'axonius.local'
WEAVE_PATH = '/usr/local/bin/weave'
DOCKER_PATH = '/usr/bin/docker'
DOCKERHUB_USER = 'nexus.pub.axonius.com/axonius'
WEAVE_VERSION = '2.6.0'
DOCKERHUB_URL = 'nexus.pub.axonius.com/'

COMPARE_MAGIC_STRING = 'compare'
MULTI_COMPARE_MAGIC_STRING = 'multicompare'

DEFAULT_SSL_CIPHERS = 'ssl_ciphers "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";\nssl_ecdh_curve secp384r1;'

SSL_CIPHERS_HIGHER_SECURITY = 'ssl_ciphers TLS-CHACHA20-POLY1305-SHA256:TLS-AES-256-GCM-SHA384:ECDHE-RSA-AES256-' \
                              'GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;\nssl_ecdh_curve secp521r1:secp384r1;'

# https://zurgl.com/how-to-set-up-an-nginx-https-website-with-an-ecdsa-certificate-and-get-an-a-rating-on-ssl-labs/
NO_RSA_SSL_CIPHERS = 'ssl_ciphers "ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:' \
    'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:' \
    'ECDHE-RSA-AES256-GCM-SHA384:' \
    'DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:' \
    'ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:' \
    'ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:' \
    'DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:' \
    'ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:' \
    'AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS:!3DES";\nssl_ecdh_curve secp521r1:secp384r1;'
