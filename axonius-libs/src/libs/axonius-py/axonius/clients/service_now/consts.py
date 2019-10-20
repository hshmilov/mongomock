TABLE_NAME_KEY = 'table_name'
DEVICE_TYPE_NAME_KEY = 'device_type_name'
DEVICES_KEY = 'devices'
TABLES_DETAILS = [{TABLE_NAME_KEY: 'cmdb_ci_computer', DEVICE_TYPE_NAME_KEY: 'Computer'},
                  {TABLE_NAME_KEY: 'cmdb_ci_vm', DEVICE_TYPE_NAME_KEY: 'Virtual Machine'},
                  {TABLE_NAME_KEY: 'cmdb_ci_vm_instance', DEVICE_TYPE_NAME_KEY: 'VCenter Virtual Machine'},
                  {TABLE_NAME_KEY: 'cmdb_ci_printer', DEVICE_TYPE_NAME_KEY: 'Printer'},
                  {TABLE_NAME_KEY: 'cmdb_ci_netgear', DEVICE_TYPE_NAME_KEY: 'Network Device'}]
NUMBER_OF_OFFSETS = 10000
OFFSET_SIZE = 200
USERS_TABLE = 'sys_user'
LOCATIONS_TABLE = 'cmn_location'
DEPARTMENTS_TABLE = 'cmn_department'
USERS_TABLE_KEY = 'users_table'
NIC_TABLE_KEY = 'cmdb_ci_network_adapter'
DEPARTMENT_TABLE_KEY = 'department_table'
LOCATION_TABLE_KEY = 'location_table'
ALM_ASSET_TABLE = 'alm_hardware'
COMPANY_TABLE = 'core_company'
# pylint: disable=C0103
INSTALL_STATUS_DICT = {'0': 'Retired',
                       '1': 'Deployed',
                       '10': 'Consumed',
                       '2': 'On Order',
                       '3': 'At Depot',
                       '6': 'In Stock',
                       '7': 'Disposed',
                       '8': 'Missing',
                       '9': 'In Transit',
                       '40': 'Decommissioned',
                       '100': 'Absent',
                       '20': 'In Build',
                       '30': 'In Use',
                       '4': 'Pending Install',
                       '5': 'Pending Repair',
                       '50': 'Removed',
                       '60': 'Absent'}
