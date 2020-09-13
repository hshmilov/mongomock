LINK_TEMPLATE = '<<ISSUE_LINK>>'
TABLE_NAME_KEY = 'table_name'
DEVICE_TYPE_NAME_KEY = 'device_type_name'
DEVICES_KEY = 'devices'
TABLES_DETAILS = [{TABLE_NAME_KEY: 'cmdb_ci_computer', DEVICE_TYPE_NAME_KEY: 'Computer'},
                  {TABLE_NAME_KEY: 'cmdb_ci_vm', DEVICE_TYPE_NAME_KEY: 'Virtual Machine'},
                  {TABLE_NAME_KEY: 'cmdb_ci_vm_instance', DEVICE_TYPE_NAME_KEY: 'VCenter Virtual Machine'},
                  {TABLE_NAME_KEY: 'cmdb_ci_printer', DEVICE_TYPE_NAME_KEY: 'Printer'},
                  {TABLE_NAME_KEY: 'cmdb_ci_netgear', DEVICE_TYPE_NAME_KEY: 'Network Device'},
                  {TABLE_NAME_KEY: 'u_cmdb_ci_computer_atm', DEVICE_TYPE_NAME_KEY: 'ATM Computer'},
                  {TABLE_NAME_KEY: 'cmdb_ci_comm', DEVICE_TYPE_NAME_KEY: 'Communication Device'},
                  {TABLE_NAME_KEY: 'cmdb_ci_cluster', DEVICE_TYPE_NAME_KEY: 'Cluster'},
                  {TABLE_NAME_KEY: 'cmdb_ci_cluster_vip', DEVICE_TYPE_NAME_KEY: 'Cluster VIP'},
                  {TABLE_NAME_KEY: 'cmdb_ci_facility_hardware', DEVICE_TYPE_NAME_KEY: 'Facility Hardware'},
                  {TABLE_NAME_KEY: 'cmdb_ci_msd', DEVICE_TYPE_NAME_KEY: 'Multi Storage Device'}]
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
LOGICALCI_TABLE = 'u_cmdb_ci_logicalci'
U_DIVISION_TABLE = 'u_division'
COMPLIANCE_EXCEPTION_TO_ASSET_TABLE = 'sn_compliance_m2m_policy_exception_control'
COMPLIANCE_EXCEPTION_TO_ASSET_TABLE_FIELDS = [
    # Note on how we connect between policy_exception with cmdb_ci asset:
    # consts.COMPLIANCE_EXCEPTION_TO_ASSET_TABLE -control->
    #  'sn_compliance_control' -profile>
    'policy_exception',
    #  'sn_grc_profile' -cmdb_ci> (cmdb_ci reference)
    'control.profile.cmdb_ci',
    # OR
    # 'sn_grc_profile' -name> (potential cmdb_ci name)
    'control.profile.name',
    # DEBUG fields for better context
    'control.profile.table', ]

COMPLIANCE_EXCEPTION_DATA_TABLE = 'sn_compliance_policy_exception'
COMPLIANCE_EXCEPTION_DATA_TABLE_FIELDS = ['sys_id', 'number', 'policy.name', 'policy_statement.name',
                                          'opened_by.name', 'short_description', 'state', 'substate',
                                          'assignment_group.name', 'active']
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

RE_SQUARED_BRACKET_WRAPPED = r'\[([^\]]+?)\]'

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

# Note: The commented sections below represent optional subtables added dynamically
#       on get_device_list according to configuration.
DEVICE_SUB_TABLES_KEY_TO_NAME = {
    LOGICALCI_TABLE: LOGICALCI_TABLE,
    # if fetch_users_info_for_devices: USERS_TABLE_KEY: USERS_TABLE,
    LOCATION_TABLE_KEY: LOCATIONS_TABLE,
    USER_GROUPS_TABLE_KEY: USER_GROUPS_TABLE,
    NIC_TABLE_KEY: NIC_TABLE_KEY,
    DEPARTMENT_TABLE_KEY: DEPARTMENTS_TABLE,
    ALM_ASSET_TABLE: ALM_ASSET_TABLE,
    COMPANY_TABLE: COMPANY_TABLE,
    IPS_TABLE: IPS_TABLE,
    CI_IPS_TABLE: CI_IPS_TABLE,
    U_SUPPLIER_TABLE: U_SUPPLIER_TABLE,
    # if fetch_ci_relations: RELATIONS_TABLE: RELATIONS_TABLE,
    MAINTENANCE_SCHED_TABLE: MAINTENANCE_SCHED_TABLE,
    SOFTWARE_PRODUCT_TABLE: SOFTWARE_PRODUCT_TABLE,
    MODEL_TABLE: MODEL_TABLE,
    # if fetch_compliance_exceptions: COMPLIANCE_EXCEPTION_TO_ASSET_TABLE: COMPLIANCE_EXCEPTION_TO_ASSET_TABLE,
    #                                 COMPLIANCE_EXCEPTION_DATA_TABLE: COMPLIANCE_EXCEPTION_DATA_TABLE,
    U_DIVISION_TABLE: U_DIVISION_TABLE,
}
USER_SUB_TABLES = {
    DEPARTMENT_TABLE_KEY: DEPARTMENTS_TABLE,
    COMPANY_TABLE: COMPANY_TABLE,
}
SUBTABLES_KEY = '_SUBTABLES'

DEFAULT_ASYNC_CHUNK_SIZE = 50

# General subtable parsing cases - table = {'sys_id': general subtable dict}
GENERIC_PARSED_SUBTABLE_KEYS = [
    USERS_TABLE_KEY, LOCATION_TABLE_KEY, USER_GROUPS_TABLE_KEY, DEPARTMENT_TABLE_KEY, ALM_ASSET_TABLE,
    COMPANY_TABLE, U_SUPPLIER_TABLE, MAINTENANCE_SCHED_TABLE, SOFTWARE_PRODUCT_TABLE, MODEL_TABLE,
    COMPLIANCE_EXCEPTION_DATA_TABLE, U_DIVISION_TABLE]

MODEL_U_CLASSIFICATION_DICT = {
    1: 'App Server',
    2: 'AS400',
    3: 'Access Control',
    4: 'App Delivery Controller',
    5: 'Backup',
    6: 'Call Manager System',
    7: 'Camera',
    8: 'Codec',
    9: 'Desktop Standard',
    10: 'Display Hardware',
    11: 'IP Firewall',
    12: 'IP Phone',
    13: 'IP Router',
    14: 'IP Switch',
    15: 'Laptop Standard',
    16: 'Mainframe',
    17: 'Monitoring Device',
    18: 'Network DDI',
    19: 'PBX',
    20: 'Power Server',
    21: 'Mobility Plan',
    22: 'Mobility Feature',
    23: 'Tap',
    24: 'Telepresence Hardware',
    25: 'Terminal Server',
    26: 'Voice Gateway',
    27: 'Voice System Hardware',
    28: 'Voicemail',
    29: 'WAN Accelerator',
    30: 'WAP Autonomous',
    31: 'WAP Controller',
    32: 'WAP Lightweight',
    33: 'Workstation Tower',
    34: 'Web Server',
    35: 'Proxy Server',
    36: 'Server',
    37: 'Tablet iOS',
    38: 'Power supply',
    39: 'Rack',
    40: 'Air Conditioning',
    41: 'Platform',
    42: 'ETL',
    43: 'FTP',
    44: 'XML',
    45: 'REST',
    46: 'SOAP',
    47: 'ESB',
    48: 'Other Web Service',
    49: 'Data circuit',
    50: 'Voice circuit',
    51: 'Database',
    52: '3rd Party Basic Connection',
    53: '3rd Party Dial Out Connection',
    54: '3rd Party Remote Connection',
    55: '3rd Party Trusted Connection',
    56: 'ATM',
    57: 'Broadband',
    58: 'Cloud Proxy',
    59: 'EWAN',
    60: 'Frame Relay',
    61: 'GCOM service',
    62: 'GDC',
    63: 'IDS Hardware',
    64: 'IP Gateway',
    65: 'ISDN',
    66: 'IVR Hardware',
    67: 'Load Balancer',
    68: 'LPAR',
    69: 'Middleware',
    70: 'MPLS',
    71: 'NetBackup',
    72: 'OVM',
    73: 'Plug-Proxy',
    74: 'SaaS',
    75: 'SONET',
    76: 'VCS',
    77: 'VPN Concentrator',
    80: 'Operating System',
    85: 'PC Image',
    89: 'Computer Accessory',
    90: 'Desktop All-in-one',
    91: 'Laptop Premium',
    92: 'Laptop Distinct',
    93: 'Workstation Mobile',
    94: 'Tablet Windows',
    95: 'ISP – DIA',
    96: 'ISP – Broadband',
    98: 'Metro Ethernet',
    99: 'Point-to-Point',
    102: 'Inbound Dedicated',
    103: 'Inbound Switched',
    104: 'Outbound Dedicated',
    105: 'Outbound Switched',
    106: 'Cloud',
    107: 'EC2',
    108: 'RDS',
    109: 'VPC',
    110: 'ELB',
    111: 'ERP',
    112: 'PLM',
    113: 'BI/DW',
    114: 'Reporting & Analytics',
    115: 'Apple Standard',
    116: 'Apple Premium',
    117: 'Apple Workstation',
    118: 'Appliance',
    119: 'NAS',
    120: 'SAN',
    121: 'Embedded Computer',
    130: 'Skype Room System',
    131: 'Compute Stick',
    132: 'Laptop Rugged',
    133: 'Tablet Rugged',
    134: 'Storage',
    135: 'IPS Hardware',
    136: 'AIX',
    137: 'Android',
    138: 'UNIX',
    139: 'IBM i',
    140: 'iOS',
    141: 'Linux',
    142: 'MacOS',
    143: 'NetWare',
    144: 'Network',
    145: 'OpenVMS',
    146: 'OS/2',
    147: 'OS/400',
    148: 'ESX',
    149: 'Windows',
    150: 'Other OS',
    151: 'Mobile Hotspot',
    152: 'Smartphone',
    153: 'Feature Phone',
    154: 'Created by MyTech Assistant',
    155: 'Internet',
    156: 'Desktop Shop Floor',
    157: 'Laptop Shop Floor',
    158: 'Inline Card',
}

BAD_ALIAS_NAME = ['iphone', 'ipad', 'samsung', 'unknown', 'service', 'sierra',
                  'sim', 'netgear', 'mobile', 'google', 'motorola', 'dell', 'test', 'missing', 'wire']
