from enum import Enum
from typing import List, Dict, Union

LINK_TEMPLATE = '<<ISSUE_LINK>>'
TABLE_NAME_KEY = 'table_name'
DEVICE_TYPE_NAME_KEY = 'device_type_name'
DEVICES_KEY = 'devices'
TABLE_NAME_BY_DEVICE_TYPE = {
    'Computer': 'cmdb_ci_computer',
    'Virtual Machine': 'cmdb_ci_vm',
    'VCenter Virtual Machine': 'cmdb_ci_vm_instance',
    'Printer': 'cmdb_ci_printer',
    'Network Device': 'cmdb_ci_netgear',
    'ATM Computer': 'u_cmdb_ci_computer_atm',
    'Communication Device': 'cmdb_ci_comm',
    'Cluster': 'cmdb_ci_cluster',
    'Cluster VIP': 'cmdb_ci_cluster_vip',
    'Facility Hardware': 'cmdb_ci_facility_hardware',
    'Multi Storage Device': 'cmdb_ci_msd',
    'VPN': 'cmdb_ci_vpn',

}

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
BUSINESS_UNIT_TABLE = 'business_unit'
COMPLIANCE_EXCEPTION_TO_ASSET_TABLE = 'sn_compliance_m2m_policy_exception_control'
# pylint: disable=line-too-long
# ServiceNow has 2 approaches for Software management, either through SAM Based software or CI, read more:
#       https://docs.servicenow.com/bundle/istanbul-it-operations-management/page/product/discovery/concept/c_DiscoSWAssetMgmtTableSchema.html
# pylint: enable=line-too-long
# Non-SAM apprach: cmdb_software_instance -software-> cmdb_ci_spkg
SOFTWARE_NO_SAM_TO_CI_TABLE = 'cmdb_software_instance'
SOFTWARE_NO_SAM_TO_CI_TABLE_FIELDS = ['installed_on.sys_id', 'software.sys_id',
                                      'software.package_name', 'software.version',
                                      'software.vendor.name', 'software.manufacturer.name']
SOFTWARE_SAM_TO_CI_TABLE = 'cmdb_sam_sw_install'
SOFTWARE_SAM_TO_CI_TABLE_FIELDS = ['installed_on.sys_id', 'sys_id', 'display_name', 'version', 'publisher', ]

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

# DOT-Walking recommandation - max 3 levels
# https://docs.servicenow.com/bundle/orlando-performance-analytics-and-reporting/page/use/reporting/concept/extended-table-fields-dot-walking.html
CONTRACT_TO_ASSET_TABLE = 'contract_rel_ci'
CONTRACT_TO_ASSET_TABLE_FIELDS = ['ci_item.sys_id', 'contract.parent.number', 'contract.number',
                                  'contract.short_description']
CONTRACT_DETAILS_TABLE_KEY = 'CONTRACT_DETAILS'

VERIFICATION_TABLE = 'x_gedrt_asset_gree_verified_personal_computer'
VERIFICATION_TABLE_FIELDS = ['configuration_item.sys_id', 'status', 'operational_status']
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
MAX_RELATIONS_DEPTH = 3

# Note: The commented sections below represent optional subtables added dynamically
#       on get_device_list according to configuration.
DEVICE_SUB_TABLES_KEY_TO_NAME = {
    VERIFICATION_TABLE: VERIFICATION_TABLE,
    # if fetch_installed_software: SOFTWARE_NO_SAM_TO_CI_TABLE: SOFTWARE_NO_SAM_TO_CI_TABLE,
    #                              SOFTWARE_SAM_TO_CI_TABLE: SOFTWARE_SAM_TO_CI_TABLE,
    # if not dotwalking: LOGICALCI_TABLE: LOGICALCI_TABLE,
    # if fetch_users_info_for_devices: USERS_TABLE_KEY: USERS_TABLE,
    # LOCATION_TABLE_KEY: LOCATIONS_TABLE,
    # if not dowalking: USER_GROUPS_TABLE_KEY: USER_GROUPS_TABLE,
    NIC_TABLE_KEY: NIC_TABLE_KEY,
    # DEPARTMENT_TABLE_KEY: DEPARTMENTS_TABLE,
    # if not dotwalking: ALM_ASSET_TABLE: ALM_ASSET_TABLE,
    # COMPANY_TABLE: COMPANY_TABLE,
    IPS_TABLE: IPS_TABLE,
    CI_IPS_TABLE: CI_IPS_TABLE,
    # if not dotwalking: U_SUPPLIER_TABLE: U_SUPPLIER_TABLE,
    # if fetch_ci_relations: RELATIONS_TABLE: RELATIONS_TABLE,
    MAINTENANCE_SCHED_TABLE: MAINTENANCE_SCHED_TABLE,
    # if fetch_software_product_model: SOFTWARE_PRODUCT_TABLE: SOFTWARE_PRODUCT_TABLE,
    # if fetch_cmdb_model: MODEL_TABLE: MODEL_TABLE,
    # if fetch_compliance_exceptions: COMPLIANCE_EXCEPTION_TO_ASSET_TABLE: COMPLIANCE_EXCEPTION_TO_ASSET_TABLE,
    #                                 COMPLIANCE_EXCEPTION_DATA_TABLE: COMPLIANCE_EXCEPTION_DATA_TABLE,
    # U_DIVISION_TABLE: U_DIVISION_TABLE,
    # if fetch_business_unit_table: BUSINESS_UNIT_TABLE: BUSINESS_UNIT_TABLE,
}
USER_SUB_TABLES = {
    DEPARTMENT_TABLE_KEY: DEPARTMENTS_TABLE,
    COMPANY_TABLE: COMPANY_TABLE,
}
SUBTABLES_KEY = '_SUBTABLES'
ADDITIONAL_SUBTABLES_WHEN_NO_DOTWALKS = {
    ALM_ASSET_TABLE: ALM_ASSET_TABLE,
    LOGICALCI_TABLE: LOGICALCI_TABLE,
    U_SUPPLIER_TABLE: U_SUPPLIER_TABLE,
    USER_GROUPS_TABLE_KEY: USER_GROUPS_TABLE,
}

USER_TABLE_FIELDS = ['sys_id', 'email', 'owned_by', 'assigned_to', 'u_director',
                     'u_manager', 'managed_by', 'u_access_authorisers', 'u_acl_contacts', 'u_bucf_contacts',
                     'u_business_owner', 'u_cmdb_data_owner', 'u_cmdb_data_steward', 'u_custodian',
                     'u_orphan_account_contacts', 'u_orphan_account_manager', 'u_primary_support_sme',
                     'u_recertification_contacts', 'u_security_administrators', 'u_technical_admin_contacts',
                     'u_uar_contacts', 'u_uav_delegates']

DEFAULT_ASYNC_CHUNK_SIZE = 50
DEFAULT_DOTWALKING_PER_REQUEST = 15
MAX_DOTWALKING_PER_REQUEST = 50
# max extra_fields query len
# ServiceNow doesnt recommend having more than 2048 chars in the whole URL
# we are restricting the sysparm_fields part to 1024 chars
# see explanation and solution with generating a view: https://hi.service-now.com/kb_view.do?sysparm_article=KB0829648
MAX_EXTRA_FIELDS_QUERY_LEN = 1024
DEFAULT_EXTRA_FIELDS_REQUIRED_LIST = ['sys_id']
# General subtable parsing cases - table = {'sys_id': general subtable dict}
GENERIC_PARSED_SUBTABLE_KEYS = [
    LOCATION_TABLE_KEY, USER_GROUPS_TABLE_KEY, DEPARTMENT_TABLE_KEY, ALM_ASSET_TABLE,
    COMPANY_TABLE, U_SUPPLIER_TABLE, MAINTENANCE_SCHED_TABLE, SOFTWARE_PRODUCT_TABLE, MODEL_TABLE,
    COMPLIANCE_EXCEPTION_DATA_TABLE, U_DIVISION_TABLE, BUSINESS_UNIT_TABLE
]

TABLE_NAME_TO_FIELDS: Dict[str, List[str]] = {
    # SOFTWARE_NO_SAM_TO_CI_TABLE: SOFTWARE_NO_SAM_TO_CI_TABLE_FIELDS,
    SOFTWARE_SAM_TO_CI_TABLE: SOFTWARE_SAM_TO_CI_TABLE_FIELDS,
    COMPLIANCE_EXCEPTION_TO_ASSET_TABLE: COMPLIANCE_EXCEPTION_TO_ASSET_TABLE_FIELDS,
    COMPLIANCE_EXCEPTION_DATA_TABLE: COMPLIANCE_EXCEPTION_DATA_TABLE_FIELDS,
    # RELATIONS_TABLE: DYNAMICALLY CALCULATED
    CONTRACT_TO_ASSET_TABLE: CONTRACT_TO_ASSET_TABLE_FIELDS,
    VERIFICATION_TABLE: VERIFICATION_TABLE_FIELDS,
}

SAMPLE_TABLES = [

]


class InjectedRawFields(Enum):
    # device fields
    support_group = 'z_support_group'
    u_director = 'z_u_director'
    u_manager = 'z_u_manager'
    u_manager_company = 'z_u_manager_company'
    u_manager_business_segment = 'z_u_manager_business_segment'
    device_model = 'z_device_model'
    snow_department = 'z_snow_department'
    physical_location = 'z_physical_location'
    u_business_segment = 'z_u_business_segment'
    owner_name = 'z_owner_name'
    owner_email = 'z_owner_email'
    assigned_to_name = 'z_assigned_to_name'
    assigned_to_u_division = 'z_assigned_to_u_division'
    assigned_to_business_unit = 'z_assigned_to_business_unit'
    assigned_to_manager = 'z_assigned_to_manager'
    manager_email = 'z_manager_email'
    u_business_unit = 'z_u_business_unit'
    assigned_to_location = 'z_assigned_to_location'
    device_managed_by = 'z_device_managed_by'
    vendor = 'z_vendor'
    device_manufacturer = 'z_device_manufacturer'
    cpu_manufacturer = 'z_cpu_manufacturer'
    company = 'z_company'
    u_supplier = 'z_u_supplier'
    maintenance_schedule = 'z_maintenance_schedule'
    u_access_authorisers = 'z_u_access_authorisers'
    u_acl_contacts = 'z_u_acl_contacts'
    u_bucf_contacts = 'z_u_bucf_contacts'
    u_business_owner = 'z_u_business_owner'
    u_cmdb_data_owner = 'z_u_cmdb_data_owner'
    u_cmdb_data_owner_group = 'z_u_cmdb_data_owner_group'
    u_cmdb_data_owner_team = 'z_u_cmdb_data_owner_team'
    u_cmdb_data_steward = 'z_u_cmdb_data_steward'
    u_custodian = 'z_u_custodian'
    u_custodian_group = 'z_u_custodian_group'
    u_fulfilment_group = 'z_u_fulfilment_group'
    u_orphan_account_contacts = 'z_u_orphan_account_contacts'
    u_orphan_account_manager = 'z_u_orphan_account_manager'
    u_primary_support_group = 'z_u_primary_support_group'
    u_primary_support_sme = 'z_u_primary_support_sme'
    u_recertification_contacts = 'z_u_recertification_contacts'
    u_security_administrators = 'z_u_security_administrators'
    u_technical_admin_contacts = 'z_u_technical_admin_contacts'
    u_toxic_division_group = 'z_u_toxic_division_group'
    u_uar_contacts = 'z_u_uar_contacts'
    u_uav_delegates = 'z_u_uav_delegates'
    snow_location = 'z_snow_location'
    snow_nics = 'z_snow_nics'
    ci_ip_data = 'z_ci_ip_data'
    snow_ips = 'z_snow_ips'
    compliance_exceptions = 'z_compliance_exceptions'
    relations = 'z_relations'
    u_it_owner_organization = 'z_u_it_owner_organization'
    u_managed_by_vendor = 'z_u_managed_by_vendor'
    ax_device_type = 'z_ax_device_type'
    u_logical_ci = 'z_u_logical_ci'
    os_title = 'z_os_title'
    major_version = 'z_major_version'
    minor_version = 'z_minor_version'
    build_version = 'z_build_version'
    model_u_classification = 'z_model_u_classification'
    asset_install_status = 'z_asset_install_status'
    asset_u_loaner = 'z_asset_u_loaner'
    asset_u_shared = 'z_asset_u_shared'
    asset_first_deployed = 'z_asset_first_deployed'
    asset_altiris_status = 'z_asset_altiris_status'
    asset_casper_status = 'z_asset_casper_status'
    asset_substatus = 'z_asset_substatus'
    asset_purchase_date = 'z_asset_purchase_date'
    asset_last_inventory = 'z_asset_last_inventory'
    assigned_to_email = 'z_assigned_to_email'
    assigned_to_country = 'z_assigned_to_country'
    snow_software = 'z_installed_software'
    u_division = 'z_u_division'
    u_level1_mgmt_org_code = 'z_u_level1_mgmt_org_code'
    u_level2_mgmt_org_code = 'z_u_level2_mgmt_org_code'
    u_level3_mgmt_org_code = 'z_u_level3_mgmt_org_code'
    u_pg_email_address = 'z_u_pg_email_address'
    contracts = 'z_contracts'
    verification_status = 'z_verification_status'
    verification_operational_status = 'z_verification_operational_status'
    connected_subnet = 'z_connected_subnet'

    # user fields
    u_company = 'z_u_company'
    u_department = 'z_u_department'


DEVICE_EXTRA_FIELDS_BY_TARGET: Dict[InjectedRawFields, Union[str, List[str]]] = {
    # Single value will be consumed per target! the first value is taken.
    InjectedRawFields.support_group: 'u_logical_ci.support_group',
    InjectedRawFields.u_director: ['support_group.u_director', 'u_logical_ci.support_group.u_director'],
    InjectedRawFields.u_manager: ['support_group.u_manager', 'u_logical_ci.support_group.u_manager'],
    InjectedRawFields.u_manager_company: ['support_group.u_manager.company',
                                          'u_logical_ci.support_group.u_manager.company'],
    InjectedRawFields.u_manager_business_segment: ['support_group.u_manager.u_business_segment',
                                                   'u_logical_ci.support_group.u_manager.u_business_segment'],
    InjectedRawFields.os_title: 'u_operating_system.title',
    InjectedRawFields.major_version: 'u_operating_system.major_version',
    InjectedRawFields.minor_version: 'u_operating_system.minor_version',
    InjectedRawFields.build_version: 'u_operating_system.build_version',
    InjectedRawFields.model_u_classification: 'model_id.u_classification',
    # InjectedRawFields.device_model: 'model_id.display_name',
    # InjectedRawFields.snow_department: 'department.name',
    # InjectedRawFields.physical_location: 'location.name',
    InjectedRawFields.asset_install_status: 'asset.install_status',
    InjectedRawFields.asset_u_loaner: 'asset.u_loaner',
    InjectedRawFields.asset_u_shared: 'asset.u_shared',
    InjectedRawFields.asset_first_deployed: 'asset.u_first_deployed',
    InjectedRawFields.asset_altiris_status: 'asset.u_altiris_status',
    InjectedRawFields.asset_casper_status: 'asset.u_casper_status',
    InjectedRawFields.asset_substatus: 'asset.substatus',
    InjectedRawFields.asset_purchase_date: 'asset.purchase_date',
    InjectedRawFields.asset_last_inventory: 'asset.u_last_inventory',
    InjectedRawFields.snow_location: 'asset.location',
    # InjectedRawFields.u_business_segment: 'u_business_segment.name',
    # InjectedRawFields.owner_name: 'owned_by.name',
    # InjectedRawFields.owner_email: 'owned_by.email',
    # InjectedRawFields.assigned_to_name: 'assigned_to.name',
    InjectedRawFields.assigned_to_email: 'assigned_to.email',
    InjectedRawFields.assigned_to_country: 'assigned_to.country',
    InjectedRawFields.assigned_to_u_division: 'assigned_to.u_division',
    InjectedRawFields.assigned_to_business_unit: 'assigned_to.u_business_unit',
    InjectedRawFields.assigned_to_manager: 'assigned_to.manager',
    # USERNAMES SUBTABLE InjectedRawFields.manager_email: 'assigned_to.manager.email'
    InjectedRawFields.assigned_to_location: 'assigned_to.location',
    # InjectedRawFields.u_business_unit: 'u_business_unit.name',
    # InjectedRawFields.device_managed_by: 'managed_by.name',
    # InjectedRawFields.vendor: 'vendor.name',
    InjectedRawFields.device_manufacturer: 'model_id.manufacturer',
    # InjectedRawFields.cpu_manufacturer: 'cpu_manufacturer.name',
    # InjectedRawFields.company: 'company.name',
    InjectedRawFields.u_supplier: ['u_supplier.u_supplier', 'u_supplier'],
    # MAINTENANCE_SCHEDULE SUBTABLE  InjectedRawFields.maintenance_schedule:
    # InjectedRawFields.u_access_authorisers: 'u_access_authorisers.name',
    # InjectedRawFields.u_acl_contacts: 'u_acl_contacts.name',
    # InjectedRawFields.u_bucf_contacts: 'u_bucf_contacts.name',
    # InjectedRawFields.u_business_owner: 'u_business_owner.name',
    # InjectedRawFields.u_cmdb_data_owner: 'u_cmdb_data_owner.name',
    # InjectedRawFields.u_cmdb_data_owner_group: 'u_cmdb_data_owner_group.name',
    # InjectedRawFields.u_cmdb_data_owner_team: 'u_cmdb_data_owner_team.name',
    # InjectedRawFields.u_cmdb_data_steward: 'u_cmdb_data_steward.name',
    # InjectedRawFields.u_custodian: 'u_custodian.name',
    # InjectedRawFields.u_custodian_group: 'u_custodian_group.name',
    # InjectedRawFields.u_fulfilment_group: 'u_fulfilment_group.name',
    # InjectedRawFields.u_orphan_account_contacts: 'u_orphan_account_contacts.name',
    # InjectedRawFields.u_orphan_account_manager: 'u_orphan_account_manager.name',
    # InjectedRawFields.u_primary_support_group: 'u_primary_support_group.name',
    # InjectedRawFields.u_primary_support_sme: 'u_primary_support_sme.name',
    # InjectedRawFields.u_recertification_contacts: 'u_recertification_contacts.name',
    # InjectedRawFields.u_security_administrators: 'u_security_administrators.name',
    # InjectedRawFields.u_technical_admin_contacts: 'u_technical_admin_contacts.name',
    # InjectedRawFields.u_toxic_division_group: 'u_toxic_division_group.name',
    # InjectedRawFields.u_uar_contacts: 'u_uar_contacts.name',
    # InjectedRawFields.u_uav_delegates: 'u_uav_delegates.name',
    # InjectedRawFields.u_it_owner_organization: 'u_it_owner_organization.name',
    # InjectedRawFields.u_managed_by_vendor: 'u_managed_by_vendor.name',
    InjectedRawFields.u_division: ['assigned_to.u_division', 'owned_by.u_division'],
    InjectedRawFields.u_level1_mgmt_org_code: ['assigned_to.u_level1_mgmt_org_code', 'owned_by.u_level1_mgmt_org_code'],
    InjectedRawFields.u_level2_mgmt_org_code: ['assigned_to.u_level2_mgmt_org_code', 'owned_by.u_level2_mgmt_org_code'],
    InjectedRawFields.u_level3_mgmt_org_code: ['assigned_to.u_level3_mgmt_org_code', 'owned_by.u_level3_mgmt_org_code'],
    InjectedRawFields.u_pg_email_address: ['assigned_to.u_pg_email_address', 'owned_by.u_pg_email_address'],
    InjectedRawFields.verification_status: 'u_verification_table_ref.status',
    InjectedRawFields.verification_operational_status: 'u_verification_table_ref.operational_status',
}

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
