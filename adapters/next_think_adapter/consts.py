DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000
MAX_NUMBER_OF_USERS = 1000000

DEFAULT_FETCH_DAYS = 3
MAXIMUM_LAST_FETCH = 7
DEFAULT_WEB_API_PORT = 1671
URL_API_PREFIX = '2'
QUERY_API_PREFIX = 'query'

USER_TABLE = 'user'
DEVICE_TABLE = 'device'

EXTRA_APPLICATIONS = 'extra_applications'
EXTRA_SERVICES = 'extra_services'

DEVICE_QUERY_FIELDS = '(id name bios_serial_number device_manufacturer device_model device_serial_number' \
                      ' device_type device_uuid first_seen ip_addresses mac_addresses last_logged_on_user' \
                      ' last_seen local_administrators number_of_cores number_of_cpus os_architecture os_build' \
                      ' os_version_and_architecture total_ram antispyware_name antivirus_name' \
                      ' chassis_serial_number device_password_required device_product_id device_product_version' \
                      ' distinguished_name entity firewall_name group_name platform sid)'
USER_QUERY_FIELDS = '(id name sid job_title department last_seen distinguished_name first_seen' \
                    ' number_of_days_since_last_seen full_name seen_on_mac seen_on_mobile seen_on_windows' \
                    ' total_active_days user_type user_uid)'
APPLICATION_QUERY_FIELDS = '(name description)'
SERVICE_QUERY_FIELDS = '(name status)'
