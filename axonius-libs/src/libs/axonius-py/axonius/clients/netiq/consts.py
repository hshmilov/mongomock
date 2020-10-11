DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 20000000

LOGIN_METHODS_LIST = ['Password', 'LDAP']
LOGIN_METHODS = {
    LOGIN_METHODS_LIST[0]: 'PASSWORD',
    LOGIN_METHODS_LIST[1]: 'LDAP_PASSWORD'
}
API_DEFAULT_EVENT = 'AdminUI'

# Using admin undocumented API, may vary and will need to contact NetIQ
# Greg - greg.morris@microfocus.com
# Another option is to investigate the request with Developer Tools (F12)
API_URL_LOGON_SUFFIX = 'user/api/auth'
API_URL_ENDPOINTS_ID_SUFFIX = 'admin/api/endpoints'
