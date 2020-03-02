DEVICE_PER_PAGE = 700
HEADERS = {'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': ''}
MAX_NUMBER_OF_DEVICES = 2000000
STR_FIELDS = {
    'created_by': 'createdBy',  # specific
    'customer': 'customer',  # specific
    'description': 'description',  # aggregated
    'device_manufacturer': 'manufacturer',  # aggregated
    'device_model': 'model',  # aggregated
    'device_serial': 'serialNumber',  # aggregated
    'facility': 'facility',  # specific
    'hostname': 'hostName',  # aggregated
    'lifecycle': 'opswLifecycle',  # specific
    'locale': 'locale',  # specific
    'name': 'name',  # aggregated
    'netbios_name': 'netBIOSName',  # specific
    'origin': 'origin',  # specific
    'os_flavor': 'osFlavor',  # specific
    'os_service_pack': 'osSPVersion',  # specific
    'os_version': 'osVersion',  # specific
    'os_platform': 'platform',  # specific
    'realm': 'realm',  # specific
    'stage': 'stage',  # specific
    'state': 'state',  # specific
    'use': 'use',  # specific
    'agent_ver': 'agentVersion',  # specific
}
DT_FIELDS = {
    'discovered_date': 'discoveredDate',  # specific
    'first_detect_dt': 'firstDetectDate',  # specific
    'last_scan_dt': 'lastScanDate',  # specific
    'created_dt': 'createdDate',  # specific
    'last_reg_dt': 'previousSWRegDate',  # specific
    'first_seen': 'createdDate',  # aggregated
    'last_seen': 'previousSWRegDate',  # aggregated
    'modified_date': 'modifiedDate'  # specific
}
BOOL_FIELDS = {
    'reboot_required': 'rebootRequired',  # specific
    'reporting': 'reporting',  # specific
    'hypervisor': 'hypervisor',  # specific
    'log_change': 'logChange',  # specific
}
IP_FIELDS = {
    'default_gw': 'defaultGw',  # aggregated
    'default_gw_ipv6': 'defaultGwIpv6',  # specific
    'loopback_ip': 'loopbackIP',  # specific
    'management_ip': 'managementIP',  # specific
    'peer_ip': 'peerIP',  # specific
    'primary_ip': 'primaryIP',  # aggregated
}
