TABLE_NAME_KEY = 'table_name'
DEVICE_TYPE_NAME_KEY = 'device_type_name'
DEVICES_KEY = 'devices'
TABLES_DETAILS = [{TABLE_NAME_KEY: 'cmdb_ci_computer', DEVICE_TYPE_NAME_KEY: 'Computer'},
                  {TABLE_NAME_KEY: 'cmdb_ci_vm', DEVICE_TYPE_NAME_KEY: 'Virtual Machine'},
                  {TABLE_NAME_KEY: 'cmdb_ci_vm_instance', DEVICE_TYPE_NAME_KEY: 'VCenter Virtual Machine'},
                  {TABLE_NAME_KEY: 'cmdb_ci_printer', DEVICE_TYPE_NAME_KEY: 'Printer'},
                  {TABLE_NAME_KEY: 'cmdb_ci_netgear', DEVICE_TYPE_NAME_KEY: 'Network Device'}]
NUMBER_OF_OFFSETS = 100000
OFFSET_SIZE = 200
USERS_TABLE = 'sys_user'
LOCATIONS_TABLE = 'cmn_location'
USER_GROUPS_TABLE = 'sys_user_group'
DEPARTMENTS_TABLE = 'cmn_department'
USERS_TABLE_KEY = 'users_table'
USERS_USERNAME_KEY = 'users_username_key'
NIC_TABLE_KEY = 'cmdb_ci_network_adapter'
DEPARTMENT_TABLE_KEY = 'department_table'
LOCATION_TABLE_KEY = 'location_table'
USER_GROUPS_TABLE_KEY = 'user_groups_table'
RELATIONS_TABLE = 'cmdb_rel_ci'
ALM_ASSET_TABLE = 'alm_hardware'
COMPANY_TABLE = 'core_company'
IPS_TABLE = 'u_ip_address'
CI_IPS_TABLE = 'cmdb_ci_ip_address'
U_SUPPLIER_TABLE = 'u_supplier'
MAINTENANCE_SCHED_TABLE = 'cmn_schedule'
SOFTWARE_PRODUCT_TABLE = 'cmdb_software_product_model'
MODEL_TABLE = 'cmdb_model'
# Note: Relations Details are performed as part of cmdb_rel_ci, they are not queried from snow separately!
RELATIONS_DETAILS_TABLE_KEY = 'RELATION_DETAILS'
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
U_HERITAGE_DICT = {'u_asset_finance': 'Asset Finance',
                   'u_bank_of_scotland': 'Bank of Scotland',
                   'u_commercial_finance': 'Commercial Finance',
                   'u_group_finance': 'Group Finance',
                   'u_halifax': 'Halifax',
                   'u_hbos': 'HBOS',
                   'u_lbg': 'LBG',
                   'u_lloyds_bank': 'Lloyds Bank',
                   'u_markets': 'Markets',
                   'na_see_virtual_items': 'N/A (See Virtual Items)',
                   'u_null': 'Null',
                   'u_scottish_widows': 'Scottish Widows',
                   'u_usa': 'USA',
                   'u_w_and_i': 'W&I'}
U_ENVIRONMENT_DICT = {'development': 'Development',
                      'dr': 'DR',
                      'end_to_end_ass_env': 'End To End Assurance Environment',
                      'na_see_virtual_items': 'N/A (See Virtual Items)',
                      'pre_live_ibm_infra_test': 'Pre-live IBM Infrastructure Test',
                      'pre_prod': 'Pre-Production',
                      'production': 'Production',
                      'rtl_app_dev': 'RTL Application Development',
                      'rtl_app_test': 'RTL Application Test',
                      'rtl_infra_dev': 'RTL Infrastructure Development',
                      'rtl_infra_test': 'RTL Infrastructure Test',
                      'test': 'Test',
                      'training': 'Training',
                      'undefined': 'undefined'}

# raw values - retrieved from original relations response
RELATIONS_TABLE_CHILD_KEY = 'child'
RELATIONS_TABLE_PARENT_KEY = 'parent'

# field names - used for put_dynamic_field
RELATIONS_FIELD_CHILD = 'downstream'
RELATIONS_FIELD_PARENT = 'upstream'

RELATIONS_KEY_TO_FIELD = {
    RELATIONS_TABLE_CHILD_KEY: RELATIONS_FIELD_CHILD,
    RELATIONS_TABLE_PARENT_KEY: RELATIONS_FIELD_PARENT,
}

DEPRECATED_RELATIVE_FIELDS = ['parents', 'children']
DEPRECATED_VALUE = []

DEVICE_SUB_TABLES_KEY_TO_NAME = {
    USERS_TABLE_KEY: USERS_TABLE,
    LOCATION_TABLE_KEY: LOCATIONS_TABLE,
    USER_GROUPS_TABLE_KEY: USER_GROUPS_TABLE,
    NIC_TABLE_KEY: NIC_TABLE_KEY,
    DEPARTMENT_TABLE_KEY: DEPARTMENTS_TABLE,
    ALM_ASSET_TABLE: ALM_ASSET_TABLE,
    COMPANY_TABLE: COMPANY_TABLE,
    IPS_TABLE: IPS_TABLE,
    CI_IPS_TABLE: CI_IPS_TABLE,
    U_SUPPLIER_TABLE: U_SUPPLIER_TABLE,
    RELATIONS_TABLE: RELATIONS_TABLE,
    MAINTENANCE_SCHED_TABLE: MAINTENANCE_SCHED_TABLE,
    SOFTWARE_PRODUCT_TABLE: SOFTWARE_PRODUCT_TABLE,
    MODEL_TABLE: MODEL_TABLE,
}
ASYNC_CHUNK_SIZE = 50
