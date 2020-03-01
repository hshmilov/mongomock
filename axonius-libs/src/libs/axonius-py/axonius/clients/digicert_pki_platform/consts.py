from pathlib import Path as __Path

DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000

WS_DEFAULT_DOMAIN = 'https://pki-ws.symauth.com/pki-ws'
WS_CERTMGMT_SERVICE = 'certificateManagementService?wsdl'

CLIENT_TRANSACTION_ID_PREFIX = 'Axonius'
DIGICERT_WEBSERVICES_CA = __Path(__file__).parent / 'cacerts'
