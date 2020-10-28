DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 20000000
MAX_WAIT_FOR_DEVICES = 30


BASE_URL = 'fnms/v1/orgs/{organization_id}'
TOKEN_URL = 'https://login.flexera.com/oidc/token'
DEVICES_URL = 'devices/installed-software'
FILES_URL = 'files/{file_name}'
ASSETS_URL = 'assets'
INVENTORIES_URL = 'inventories'
TOKEN_TIMEOUT_MIN = 60
SLEEP_TIME_SEC = 2  # According to documentation (from the developers)
# there should be 2 seconds apart between each request

ASSET_FIELD = 'extra_assets'
TYPE_FIELD = 'extra_type'
DEVICE_TYPE = 'device'
INVENTORY_TYPE = 'inventory'
COMPLETED_STATUS = 'Completed'
