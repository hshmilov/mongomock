from json_file_adapter.service import FILE_NAME, USERS_DATA, DEVICES_DATA
from test_helpers.file_mock_credentials import FileForCredentialsMock

cisco_ssh_creds = {
    'host': '192.168.20.42',
    'protocol': 'ssh',
    'username': 'cisco',
    'password': 'cisco',
}

cisco_creds = {
    'host': '192.168.20.42',
    'community': 'public',
}

cisco_v3_creds = {
    'host': '192.168.20.42',
    'auth_passphrase': 'user1234',
    'priv_passphrase': 'user1234',
}

SOME_DEVICE_ID = 'arp_E8:1C:BA:EA:42:5A'

cisco_json_file_mock_credentials = {
    FILE_NAME: "CISCO_MOCK",
    USERS_DATA: FileForCredentialsMock(USERS_DATA, ''),
    DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, """
    {
    "devices": [
        {
            "accurate_for_datetime": "2020-05-13 19:05:53",
            "first_fetch_time": "2020-05-13 19:05:53",
            "adapter_properties": [
                "Network"
            ],
            "fetch_proto": "ARP",
            "quick_id": "cisco_adapter_0!arp_E8:1C:BA:EA:42:66",
            "os": {
                "os_str": "none"
            },
            "id": "arp_E8:1C:BA:EA:42:66",
            "plugin_type": "Adapter",
            "network_interfaces": [
                {
                    "manufacturer": "Fortinet (Fortinet, Inc.)",
                    "mac": "E8:1C:BA:EA:42:66"
                }
            ],
            "fetch_time": "2020-05-13 19:05:53",
            "related_ips": {
                "ips_raw": [
                    3232238081,
                    3232238081
                ],
                "ips": [
                    "192.168.10.1",
                    "192.168.10.1"
                ]
            },
            "connected_devices": [
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                },
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                }
            ],
            "plugin_unique_name": "cisco_adapter_0",
            "plugin_name": "cisco_adapter",
            "client_used": "192.168.20.42",
            "pretty_id": "AX-1",
            "type": "entitydata"
        },
        {
            "accurate_for_datetime": "2020-05-13 19:05:53",
            "first_fetch_time": "2020-05-13 19:05:53",
            "adapter_properties": [
                "Network"
            ],
            "fetch_proto": "ARP",
            "quick_id": "cisco_adapter_0!arp_E8:1C:BA:EA:42:5A",
            "os": {
                "os_str": "none"
            },
            "id": "arp_E8:1C:BA:EA:42:5A",
            "plugin_type": "Adapter",
            "network_interfaces": [
                {
                    "manufacturer": "Fortinet (Fortinet, Inc.)",
                    "mac": "E8:1C:BA:EA:42:5A"
                }
            ],
            "fetch_time": "2020-05-13 19:05:53",
            "related_ips": {
                "ips_raw": [
                    3232240641,
                    3232240641
                ],
                "ips": [
                    "192.168.20.1",
                    "192.168.20.1"
                ]
            },
            "connected_devices": [
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                },
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                }
            ],
            "plugin_unique_name": "cisco_adapter_0",
            "plugin_name": "cisco_adapter",
            "client_used": "192.168.20.42",
            "pretty_id": "AX-3",
            "type": "entitydata"
        },
        {
            "accurate_for_datetime": "2020-05-13 19:05:53",
            "first_fetch_time": "2020-05-13 19:05:53",
            "adapter_properties": [
                "Network"
            ],
            "fetch_proto": "ARP",
            "quick_id": "cisco_adapter_0!arp_00:50:56:91:76:E3",
            "os": {
                "os_str": "none"
            },
            "id": "arp_00:50:56:91:76:E3",
            "plugin_type": "Adapter",
            "network_interfaces": [
                {
                    "manufacturer": "VMware (VMware, Inc.)",
                    "mac": "00:50:56:91:76:E3"
                }
            ],
            "fetch_time": "2020-05-13 19:05:53",
            "related_ips": {
                "ips_raw": [
                    3232240670,
                    3232240670
                ],
                "ips": [
                    "192.168.20.30",
                    "192.168.20.30"
                ]
            },
            "connected_devices": [
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                },
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                }
            ],
            "plugin_unique_name": "cisco_adapter_0",
            "plugin_name": "cisco_adapter",
            "client_used": "192.168.20.42",
            "pretty_id": "AX-4",
            "type": "entitydata"
        },
        {
            "accurate_for_datetime": "2020-05-13 19:05:53",
            "first_fetch_time": "2020-05-13 19:05:53",
            "adapter_properties": [
                "Network"
            ],
            "fetch_proto": "ARP",
            "quick_id": "cisco_adapter_0!arp_00:50:56:91:0B:D1",
            "os": {
                "os_str": "none"
            },
            "id": "arp_00:50:56:91:0B:D1",
            "plugin_type": "Adapter",
            "network_interfaces": [
                {
                    "manufacturer": "VMware (VMware, Inc.)",
                    "mac": "00:50:56:91:0B:D1"
                }
            ],
            "fetch_time": "2020-05-13 19:05:53",
            "related_ips": {
                "ips_raw": [
                    3232240681,
                    3232240681
                ],
                "ips": [
                    "192.168.20.41",
                    "192.168.20.41"
                ]
            },
            "connected_devices": [
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                },
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                }
            ],
            "plugin_unique_name": "cisco_adapter_0",
            "plugin_name": "cisco_adapter",
            "client_used": "192.168.20.42",
            "pretty_id": "AX-5",
            "type": "entitydata"
        },
        {
            "accurate_for_datetime": "2020-05-13 19:05:53",
            "first_fetch_time": "2020-05-13 19:05:53",
            "adapter_properties": [
                "Network"
            ],
            "fetch_proto": "ARP",
            "quick_id": "cisco_adapter_0!arp_00:50:56:91:A6:6B",
            "os": {
                "os_str": "none"
            },
            "id": "arp_00:50:56:91:A6:6B",
            "plugin_type": "Adapter",
            "network_interfaces": [
                {
                    "manufacturer": "VMware (VMware, Inc.)",
                    "mac": "00:50:56:91:A6:6B"
                }
            ],
            "fetch_time": "2020-05-13 19:05:53",
            "related_ips": {
                "ips_raw": [
                    3232240692,
                    3232240692
                ],
                "ips": [
                    "192.168.20.52",
                    "192.168.20.52"
                ]
            },
            "connected_devices": [
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                },
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                }
            ],
            "plugin_unique_name": "cisco_adapter_0",
            "plugin_name": "cisco_adapter",
            "client_used": "192.168.20.42",
            "pretty_id": "AX-7",
            "type": "entitydata"
        },
        {
            "accurate_for_datetime": "2020-05-13 19:05:53",
            "first_fetch_time": "2020-05-13 19:05:53",
            "adapter_properties": [
                "Network"
            ],
            "fetch_proto": "ARP",
            "quick_id": "cisco_adapter_0!arp_00:90:0B:4E:83:22",
            "os": {
                "os_str": "none"
            },
            "id": "arp_00:90:0B:4E:83:22",
            "plugin_type": "Adapter",
            "network_interfaces": [
                {
                    "manufacturer": "LannerEl (Lanner Electronics, Inc.)",
                    "mac": "00:90:0B:4E:83:22"
                }
            ],
            "fetch_time": "2020-05-13 19:05:53",
            "related_ips": {
                "ips_raw": [
                    3232240889,
                    3232240889
                ],
                "ips": [
                    "192.168.20.249",
                    "192.168.20.249"
                ]
            },
            "connected_devices": [
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                },
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                }
            ],
            "plugin_unique_name": "cisco_adapter_0",
            "plugin_name": "cisco_adapter",
            "client_used": "192.168.20.42",
            "pretty_id": "AX-8",
            "type": "entitydata"
        },
        {
            "accurate_for_datetime": "2020-05-13 19:05:53",
            "first_fetch_time": "2020-05-13 19:05:53",
            "adapter_properties": [
                "Network"
            ],
            "fetch_proto": "ARP",
            "quick_id": "cisco_adapter_0!arp_00:1B:8F:DF:DF:40",
            "os": {
                "os_str": "none"
            },
            "id": "arp_00:1B:8F:DF:DF:40",
            "plugin_type": "Adapter",
            "hostname": "Axonius-TLV.axonius.lan",
            "network_interfaces": [
                {
                    "manufacturer": "Cisco (Cisco Systems, Inc)",
                    "mac": "00:1B:8F:DF:DF:40"
                },
                {
                    "mac": "00:1B:8F:DF:DF:41",
                    "ips": ["192.168.20.42"],
                    "subnets": ["192.168.20.0/24"],
                    "manufacturer": "Cisco (Cisco Systems, Inc)",
                    "name": "Vlan2"
                }
            ],
            "fetch_time": "2020-05-13 19:05:53",
            "related_ips": {
                "ips_raw": [
                    3232238086,
                    3232238086
                ],
                "ips": [
                    "192.168.10.6",
                    "192.168.10.6"
                ]
            },
            "connected_devices": [
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                },
                {
                    "remote_name": "192.168.20.42",
                    "connection_type": "Indirect"
                }
            ],
            "plugin_unique_name": "cisco_adapter_0",
            "plugin_name": "cisco_adapter",
            "client_used": "192.168.20.42",
            "pretty_id": "AX-2",
            "type": "entitydata",
			"port_access": [
				{
					"name": "porttest",
					"port_mode": "singleHost"
				}
			]
        }
    ],
	
	"fields": ["adapters","adapter_list_length","internal_axon_id","last_seen","fetch_time","first_fetch_time","network_interfaces","network_interfaces.name","network_interfaces.mac","network_interfaces.manufacturer","network_interfaces.ips","network_interfaces.subnets","network_interfaces.vlan_list","network_interfaces.vlan_list.name","network_interfaces.vlan_list.tagid","network_interfaces.vlan_list.tagness","network_interfaces.operational_status","network_interfaces.admin_status","network_interfaces.speed","network_interfaces.port_type","network_interfaces.mtu","network_interfaces.gateway","network_interfaces.port","os.type","os.distribution","os.is_windows_server","os.os_str","os.bitness","os.sp","os.install_date","os.kernel_version","os.codename","os.major","os.minor","os.build","os.serial","connected_devices","connected_devices.remote_name","connected_devices.local_ifaces","connected_devices.local_ifaces.name","connected_devices.local_ifaces.mac","connected_devices.local_ifaces.manufacturer","connected_devices.local_ifaces.ips","connected_devices.local_ifaces.subnets","connected_devices.local_ifaces.vlan_list","connected_devices.local_ifaces.vlan_list.name","connected_devices.local_ifaces.vlan_list.tagid","connected_devices.local_ifaces.vlan_list.tagness","connected_devices.local_ifaces.operational_status","connected_devices.local_ifaces.admin_status","connected_devices.local_ifaces.speed","connected_devices.local_ifaces.port_type","connected_devices.local_ifaces.mtu","connected_devices.local_ifaces.gateway","connected_devices.local_ifaces.port","connected_devices.remote_ifaces","connected_devices.remote_ifaces.name","connected_devices.remote_ifaces.mac","connected_devices.remote_ifaces.manufacturer","connected_devices.remote_ifaces.ips","connected_devices.remote_ifaces.subnets","connected_devices.remote_ifaces.vlan_list","connected_devices.remote_ifaces.vlan_list.name","connected_devices.remote_ifaces.vlan_list.tagid","connected_devices.remote_ifaces.vlan_list.tagness","connected_devices.remote_ifaces.operational_status","connected_devices.remote_ifaces.admin_status","connected_devices.remote_ifaces.speed","connected_devices.remote_ifaces.port_type","connected_devices.remote_ifaces.mtu","connected_devices.remote_ifaces.gateway","connected_devices.remote_ifaces.port","connected_devices.connection_type","id","related_ips.name","related_ips.mac","related_ips.manufacturer","related_ips.ips","related_ips.subnets","related_ips.vlan_list","related_ips.vlan_list.name","related_ips.vlan_list.tagid","related_ips.vlan_list.tagness","related_ips.operational_status","related_ips.admin_status","related_ips.speed","related_ips.port_type","related_ips.mtu","related_ips.gateway","related_ips.port","device_model","device_serial","adapter_properties","port_access","port_access.name","port_access.port_mode","port_access.operation_vlan_type","port_access.guest_vlan_number","port_access.auth_fail_vlan_number","port_access.operation_vlan_number","port_access.shutdown_timeout_enabled","port_access.auth_fail_max_attempts","labels","hostname_preferred","os.type_preferred","os.distribution_preferred","network_interfaces.mac_preferred","network_interfaces.ips_preferred","correlation_reasons"],
	"additional_schema": [{"enum":["ARP","CDP","DHCP","CLIENT","PRIME_CLIENT","PRIME_WIFI_CLIENT"],"name":"fetch_proto","title":"Fetch Protocol","type":"string"},{"format":"date-time","name":"last_seen","title":"Last Seen","type":"string"},{"format":"date-time","name":"fetch_time","title":"Fetch Time","type":"string"},{"format":"date-time","name":"first_fetch_time","title":"First Fetch Time","type":"string"},{"format":"table","items":{"items":[{"name":"name","title":"Iface Name","type":"string"},{"name":"mac","title":"MAC","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"ips","title":"IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"subnets","title":"Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"vlan_list","title":"Vlans","type":"array"},{"branched":true,"name":"vlan_list.name","title":"Vlans: Vlan Name","type":"string"},{"branched":true,"name":"vlan_list.tagid","title":"Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"vlan_list.tagness","title":"Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"operational_status","title":"Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"admin_status","title":"Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"speed","title":"Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"port_type","title":"Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"mtu","title":"MTU","type":"string"},{"name":"gateway","title":"Gateway","type":"string"},{"name":"port","title":"Port","type":"string"}],"type":"array"},"name":"network_interfaces","title":"Network Interfaces","type":"array"},{"branched":true,"name":"network_interfaces.name","title":"Network Interfaces: Iface Name","type":"string"},{"branched":true,"name":"network_interfaces.mac","title":"Network Interfaces: MAC","type":"string"},{"branched":true,"name":"network_interfaces.manufacturer","title":"Network Interfaces: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"network_interfaces.ips","title":"Network Interfaces: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"network_interfaces.subnets","title":"Network Interfaces: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"network_interfaces.vlan_list","title":"Network Interfaces: Vlans","type":"array"},{"branched":true,"name":"network_interfaces.vlan_list.name","title":"Network Interfaces: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"network_interfaces.vlan_list.tagid","title":"Network Interfaces: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"network_interfaces.vlan_list.tagness","title":"Network Interfaces: Vlans: Vlan Tagness","type":"string"},{"branched":true,"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"network_interfaces.operational_status","title":"Network Interfaces: Operational Status","type":"string"},{"branched":true,"enum":["Up","Down","Testing"],"name":"network_interfaces.admin_status","title":"Network Interfaces: Admin Status","type":"string"},{"branched":true,"description":"Interface max speed per Second","name":"network_interfaces.speed","title":"Network Interfaces: Interface Speed","type":"string"},{"branched":true,"enum":["Access","Trunk"],"name":"network_interfaces.port_type","title":"Network Interfaces: Port Type","type":"string"},{"branched":true,"description":"Interface Maximum transmission unit","name":"network_interfaces.mtu","title":"Network Interfaces: MTU","type":"string"},{"branched":true,"name":"network_interfaces.gateway","title":"Network Interfaces: Gateway","type":"string"},{"branched":true,"name":"network_interfaces.port","title":"Network Interfaces: Port","type":"string"},{"enum":["Windows","Linux","OS X","iOS","AirOS","Android","FreeBSD","VMWare","Cisco","Mikrotik","VxWorks","PanOS","F5 Networks Big-IP","Solaris","AIX","Printer","PlayStation","Check Point","Arista","Netscaler"],"name":"os.type","title":"OS: Type","type":"string"},{"name":"os.distribution","title":"OS: Distribution","type":"string"},{"name":"os.is_windows_server","title":"OS: Is Windows Server","type":"bool"},{"name":"os.os_str","title":"OS: Full OS String","type":"string"},{"enum":[32,64],"name":"os.bitness","title":"OS: Bitness","type":"integer"},{"name":"os.sp","title":"OS: Service Pack","type":"string"},{"format":"date-time","name":"os.install_date","title":"OS: Install Date","type":"string"},{"name":"os.kernel_version","title":"OS: Kernel Version","type":"string"},{"name":"os.codename","title":"OS: Code name","type":"string"},{"name":"os.major","title":"OS: Major","type":"integer"},{"name":"os.minor","title":"OS: Minor","type":"integer"},{"name":"os.build","title":"OS: Build","type":"string"},{"name":"os.serial","title":"OS: Serial","type":"string"},{"format":"table","items":{"items":[{"name":"remote_name","title":"Remote Device Name","type":"string"},{"items":{"items":[{"name":"name","title":"Iface Name","type":"string"},{"name":"mac","title":"MAC","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"ips","title":"IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"subnets","title":"Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"vlan_list","title":"Vlans","type":"array"},{"branched":true,"name":"vlan_list.name","title":"Vlans: Vlan Name","type":"string"},{"branched":true,"name":"vlan_list.tagid","title":"Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"vlan_list.tagness","title":"Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"operational_status","title":"Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"admin_status","title":"Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"speed","title":"Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"port_type","title":"Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"mtu","title":"MTU","type":"string"},{"name":"gateway","title":"Gateway","type":"string"},{"name":"port","title":"Port","type":"string"}],"type":"array"},"name":"local_ifaces","title":"Local Interface","type":"array"},{"branched":true,"name":"local_ifaces.name","title":"Local Interface: Iface Name","type":"string"},{"branched":true,"name":"local_ifaces.mac","title":"Local Interface: MAC","type":"string"},{"branched":true,"name":"local_ifaces.manufacturer","title":"Local Interface: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"local_ifaces.ips","title":"Local Interface: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"local_ifaces.subnets","title":"Local Interface: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"local_ifaces.vlan_list","title":"Local Interface: Vlans","type":"array"},{"branched":true,"name":"local_ifaces.vlan_list.name","title":"Local Interface: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"local_ifaces.vlan_list.tagid","title":"Local Interface: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"local_ifaces.vlan_list.tagness","title":"Local Interface: Vlans: Vlan Tagness","type":"string"},{"branched":true,"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"local_ifaces.operational_status","title":"Local Interface: Operational Status","type":"string"},{"branched":true,"enum":["Up","Down","Testing"],"name":"local_ifaces.admin_status","title":"Local Interface: Admin Status","type":"string"},{"branched":true,"description":"Interface max speed per Second","name":"local_ifaces.speed","title":"Local Interface: Interface Speed","type":"string"},{"branched":true,"enum":["Access","Trunk"],"name":"local_ifaces.port_type","title":"Local Interface: Port Type","type":"string"},{"branched":true,"description":"Interface Maximum transmission unit","name":"local_ifaces.mtu","title":"Local Interface: MTU","type":"string"},{"branched":true,"name":"local_ifaces.gateway","title":"Local Interface: Gateway","type":"string"},{"branched":true,"name":"local_ifaces.port","title":"Local Interface: Port","type":"string"},{"items":{"items":[{"name":"name","title":"Iface Name","type":"string"},{"name":"mac","title":"MAC","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"ips","title":"IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"subnets","title":"Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"vlan_list","title":"Vlans","type":"array"},{"branched":true,"name":"vlan_list.name","title":"Vlans: Vlan Name","type":"string"},{"branched":true,"name":"vlan_list.tagid","title":"Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"vlan_list.tagness","title":"Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"operational_status","title":"Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"admin_status","title":"Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"speed","title":"Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"port_type","title":"Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"mtu","title":"MTU","type":"string"},{"name":"gateway","title":"Gateway","type":"string"},{"name":"port","title":"Port","type":"string"}],"type":"array"},"name":"remote_ifaces","title":"Remote Device Iface","type":"array"},{"branched":true,"name":"remote_ifaces.name","title":"Remote Device Iface: Iface Name","type":"string"},{"branched":true,"name":"remote_ifaces.mac","title":"Remote Device Iface: MAC","type":"string"},{"branched":true,"name":"remote_ifaces.manufacturer","title":"Remote Device Iface: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"remote_ifaces.ips","title":"Remote Device Iface: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"remote_ifaces.subnets","title":"Remote Device Iface: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"remote_ifaces.vlan_list","title":"Remote Device Iface: Vlans","type":"array"},{"branched":true,"name":"remote_ifaces.vlan_list.name","title":"Remote Device Iface: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"remote_ifaces.vlan_list.tagid","title":"Remote Device Iface: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"remote_ifaces.vlan_list.tagness","title":"Remote Device Iface: Vlans: Vlan Tagness","type":"string"},{"branched":true,"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"remote_ifaces.operational_status","title":"Remote Device Iface: Operational Status","type":"string"},{"branched":true,"enum":["Up","Down","Testing"],"name":"remote_ifaces.admin_status","title":"Remote Device Iface: Admin Status","type":"string"},{"branched":true,"description":"Interface max speed per Second","name":"remote_ifaces.speed","title":"Remote Device Iface: Interface Speed","type":"string"},{"branched":true,"enum":["Access","Trunk"],"name":"remote_ifaces.port_type","title":"Remote Device Iface: Port Type","type":"string"},{"branched":true,"description":"Interface Maximum transmission unit","name":"remote_ifaces.mtu","title":"Remote Device Iface: MTU","type":"string"},{"branched":true,"name":"remote_ifaces.gateway","title":"Remote Device Iface: Gateway","type":"string"},{"branched":true,"name":"remote_ifaces.port","title":"Remote Device Iface: Port","type":"string"},{"enum":["Direct","Indirect"],"name":"connection_type","title":"Connection Type","type":"string"}],"type":"array"},"name":"connected_devices","title":"Connected Devices","type":"array"},{"branched":true,"name":"connected_devices.remote_name","title":"Connected Devices: Remote Device Name","type":"string"},{"items":{"items":[{"name":"name","title":"Iface Name","type":"string"},{"name":"mac","title":"MAC","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"ips","title":"IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"subnets","title":"Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"vlan_list","title":"Vlans","type":"array"},{"branched":true,"name":"vlan_list.name","title":"Vlans: Vlan Name","type":"string"},{"branched":true,"name":"vlan_list.tagid","title":"Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"vlan_list.tagness","title":"Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"operational_status","title":"Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"admin_status","title":"Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"speed","title":"Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"port_type","title":"Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"mtu","title":"MTU","type":"string"},{"name":"gateway","title":"Gateway","type":"string"},{"name":"port","title":"Port","type":"string"}],"type":"array"},"name":"connected_devices.local_ifaces","title":"Connected Devices: Local Interface","type":"array"},{"branched":true,"name":"connected_devices.local_ifaces.name","title":"Connected Devices: Local Interface: Iface Name","type":"string"},{"branched":true,"name":"connected_devices.local_ifaces.mac","title":"Connected Devices: Local Interface: MAC","type":"string"},{"branched":true,"name":"connected_devices.local_ifaces.manufacturer","title":"Connected Devices: Local Interface: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"connected_devices.local_ifaces.ips","title":"Connected Devices: Local Interface: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"connected_devices.local_ifaces.subnets","title":"Connected Devices: Local Interface: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"connected_devices.local_ifaces.vlan_list","title":"Connected Devices: Local Interface: Vlans","type":"array"},{"branched":true,"name":"connected_devices.local_ifaces.vlan_list.name","title":"Connected Devices: Local Interface: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"connected_devices.local_ifaces.vlan_list.tagid","title":"Connected Devices: Local Interface: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"connected_devices.local_ifaces.vlan_list.tagness","title":"Connected Devices: Local Interface: Vlans: Vlan Tagness","type":"string"},{"branched":true,"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"connected_devices.local_ifaces.operational_status","title":"Connected Devices: Local Interface: Operational Status","type":"string"},{"branched":true,"enum":["Up","Down","Testing"],"name":"connected_devices.local_ifaces.admin_status","title":"Connected Devices: Local Interface: Admin Status","type":"string"},{"branched":true,"description":"Interface max speed per Second","name":"connected_devices.local_ifaces.speed","title":"Connected Devices: Local Interface: Interface Speed","type":"string"},{"branched":true,"enum":["Access","Trunk"],"name":"connected_devices.local_ifaces.port_type","title":"Connected Devices: Local Interface: Port Type","type":"string"},{"branched":true,"description":"Interface Maximum transmission unit","name":"connected_devices.local_ifaces.mtu","title":"Connected Devices: Local Interface: MTU","type":"string"},{"branched":true,"name":"connected_devices.local_ifaces.gateway","title":"Connected Devices: Local Interface: Gateway","type":"string"},{"branched":true,"name":"connected_devices.local_ifaces.port","title":"Connected Devices: Local Interface: Port","type":"string"},{"items":{"items":[{"name":"name","title":"Iface Name","type":"string"},{"name":"mac","title":"MAC","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"ips","title":"IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"subnets","title":"Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"vlan_list","title":"Vlans","type":"array"},{"branched":true,"name":"vlan_list.name","title":"Vlans: Vlan Name","type":"string"},{"branched":true,"name":"vlan_list.tagid","title":"Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"vlan_list.tagness","title":"Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"operational_status","title":"Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"admin_status","title":"Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"speed","title":"Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"port_type","title":"Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"mtu","title":"MTU","type":"string"},{"name":"gateway","title":"Gateway","type":"string"},{"name":"port","title":"Port","type":"string"}],"type":"array"},"name":"connected_devices.remote_ifaces","title":"Connected Devices: Remote Device Iface","type":"array"},{"branched":true,"name":"connected_devices.remote_ifaces.name","title":"Connected Devices: Remote Device Iface: Iface Name","type":"string"},{"branched":true,"name":"connected_devices.remote_ifaces.mac","title":"Connected Devices: Remote Device Iface: MAC","type":"string"},{"branched":true,"name":"connected_devices.remote_ifaces.manufacturer","title":"Connected Devices: Remote Device Iface: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"connected_devices.remote_ifaces.ips","title":"Connected Devices: Remote Device Iface: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"connected_devices.remote_ifaces.subnets","title":"Connected Devices: Remote Device Iface: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"connected_devices.remote_ifaces.vlan_list","title":"Connected Devices: Remote Device Iface: Vlans","type":"array"},{"branched":true,"name":"connected_devices.remote_ifaces.vlan_list.name","title":"Connected Devices: Remote Device Iface: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"connected_devices.remote_ifaces.vlan_list.tagid","title":"Connected Devices: Remote Device Iface: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"connected_devices.remote_ifaces.vlan_list.tagness","title":"Connected Devices: Remote Device Iface: Vlans: Vlan Tagness","type":"string"},{"branched":true,"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"connected_devices.remote_ifaces.operational_status","title":"Connected Devices: Remote Device Iface: Operational Status","type":"string"},{"branched":true,"enum":["Up","Down","Testing"],"name":"connected_devices.remote_ifaces.admin_status","title":"Connected Devices: Remote Device Iface: Admin Status","type":"string"},{"branched":true,"description":"Interface max speed per Second","name":"connected_devices.remote_ifaces.speed","title":"Connected Devices: Remote Device Iface: Interface Speed","type":"string"},{"branched":true,"enum":["Access","Trunk"],"name":"connected_devices.remote_ifaces.port_type","title":"Connected Devices: Remote Device Iface: Port Type","type":"string"},{"branched":true,"description":"Interface Maximum transmission unit","name":"connected_devices.remote_ifaces.mtu","title":"Connected Devices: Remote Device Iface: MTU","type":"string"},{"branched":true,"name":"connected_devices.remote_ifaces.gateway","title":"Connected Devices: Remote Device Iface: Gateway","type":"string"},{"branched":true,"name":"connected_devices.remote_ifaces.port","title":"Connected Devices: Remote Device Iface: Port","type":"string"},{"branched":true,"enum":["Direct","Indirect"],"name":"connected_devices.connection_type","title":"Connected Devices: Connection Type","type":"string"},{"name":"id","title":"ID","type":"string"},{"name":"related_ips.name","title":"Related Ips: Iface Name","type":"string"},{"name":"related_ips.mac","title":"Related Ips: MAC","type":"string"},{"name":"related_ips.manufacturer","title":"Related Ips: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"related_ips.ips","title":"Related Ips: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"related_ips.subnets","title":"Related Ips: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"related_ips.vlan_list","title":"Related Ips: Vlans","type":"array"},{"branched":true,"name":"related_ips.vlan_list.name","title":"Related Ips: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"related_ips.vlan_list.tagid","title":"Related Ips: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"related_ips.vlan_list.tagness","title":"Related Ips: Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"related_ips.operational_status","title":"Related Ips: Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"related_ips.admin_status","title":"Related Ips: Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"related_ips.speed","title":"Related Ips: Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"related_ips.port_type","title":"Related Ips: Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"related_ips.mtu","title":"Related Ips: MTU","type":"string"},{"name":"related_ips.gateway","title":"Related Ips: Gateway","type":"string"},{"name":"related_ips.port","title":"Related Ips: Port","type":"string"},{"name":"device_model","title":"Device Model","type":"string"},{"name":"device_serial","title":"Device Manufacturer Serial","type":"string"},{"enum":["Agent","Endpoint_Protection_Platform","Network","Firewall","Manager","Vulnerability_Assessment","Assets","UserManagement","Cloud_Provider","Virtualization","MDM"],"items":{"enum":["Agent","Endpoint_Protection_Platform","Network","Firewall","Manager","Vulnerability_Assessment","Assets","UserManagement","Cloud_Provider","Virtualization","MDM"],"type":"string"},"name":"adapter_properties","title":"Adapter Properties","type":"array"},{"format":"table","items":{"items":[{"name":"name","title":"Interface Name","type":"string"},{"enum":["singleHost","multiHost","multiAuth","other"],"name":"port_mode","title":"Port Mode","type":"string"},{"enum":["other","operational","guest","authFail"],"name":"operation_vlan_type","title":"Port Type","type":"integer"},{"description":"Specifies the Guest Vlan of the interface.  An interface with cpaePortMode value of 'singleHost' will be moved to its Guest Vlan if the supplicant on the interface is not capable of IEEE-802.1x authentication.  A value of zero for this object indicates no Guest Vlan configured for the interface.","name":"guest_vlan_number","title":"Guest Vlan","type":"integer"},{"description":"Specifies the Auth-Fail (Authentication Fail) Vlan of the port.  A port is moved to Auth-Fail Vlan if the supplicant which support IEEE-802.1x authentication is unsuccessfully authenticated. A value of zero for this object indicates no Auth-Fail Vlan configured for the port.","name":"auth_fail_vlan_number","title":"Auth Failed vlan","type":"integer"},{"description":"The VlanIndex of the Vlan which is assigned to this port via IEEE-802.1x and related methods of authentication supported by the system.  A value of zero for this object indicates that no Vlan is assigned to this port via IEEE-802.1x authentication.","name":"operation_vlan_number","title":"Operational vlan","type":"integer"},{"description":"Specifies whether shutdown timeout feature is enabled on the interface.","name":"shutdown_timeout_enabled","title":"Shutdown Timeout Enabled","type":"bool"},{"description":"Specifies the maximum number of authentication attempts should be made before the port is moved into the Auth-Fail Vlan.","name":"auth_fail_max_attempts","title":"Auth Fail Max Attempts","type":"integer"}],"type":"array"},"name":"port_access","title":"Port Access","type":"array"},{"branched":true,"name":"port_access.name","title":"Port Access: Interface Name","type":"string"},{"branched":true,"enum":["singleHost","multiHost","multiAuth","other"],"name":"port_access.port_mode","title":"Port Access: Port Mode","type":"string"},{"branched":true,"enum":["other","operational","guest","authFail"],"name":"port_access.operation_vlan_type","title":"Port Access: Port Type","type":"integer"},{"branched":true,"description":"Specifies the Guest Vlan of the interface.  An interface with cpaePortMode value of 'singleHost' will be moved to its Guest Vlan if the supplicant on the interface is not capable of IEEE-802.1x authentication.  A value of zero for this object indicates no Guest Vlan configured for the interface.","name":"port_access.guest_vlan_number","title":"Port Access: Guest Vlan","type":"integer"},{"branched":true,"description":"Specifies the Auth-Fail (Authentication Fail) Vlan of the port.  A port is moved to Auth-Fail Vlan if the supplicant which support IEEE-802.1x authentication is unsuccessfully authenticated. A value of zero for this object indicates no Auth-Fail Vlan configured for the port.","name":"port_access.auth_fail_vlan_number","title":"Port Access: Auth Failed vlan","type":"integer"},{"branched":true,"description":"The VlanIndex of the Vlan which is assigned to this port via IEEE-802.1x and related methods of authentication supported by the system.  A value of zero for this object indicates that no Vlan is assigned to this port via IEEE-802.1x authentication.","name":"port_access.operation_vlan_number","title":"Port Access: Operational vlan","type":"integer"},{"branched":true,"description":"Specifies whether shutdown timeout feature is enabled on the interface.","name":"port_access.shutdown_timeout_enabled","title":"Port Access: Shutdown Timeout Enabled","type":"bool"},{"branched":true,"description":"Specifies the maximum number of authentication attempts should be made before the port is moved into the Auth-Fail Vlan.","name":"port_access.auth_fail_max_attempts","title":"Port Access: Auth Fail Max Attempts","type":"integer"},{"name":"adapter_count","title":"Distinct Adapter Connections Count","type":"number"}],
	"raw_fields": []
}
    """)
}
