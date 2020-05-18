from json_file_adapter.service import FILE_NAME, USERS_DATA, DEVICES_DATA
from test_helpers.file_mock_credentials import FileForCredentialsMock

crowd_strike_json_file_mock_devices = {
    FILE_NAME: 'CROWD_STRIKE_MOCK',
    USERS_DATA: FileForCredentialsMock(USERS_DATA, ''),
    DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, '''{
    "devices": [
        {
            "connected_devices": [],
            "device_manufacturer": "Phoenix Technologies LTD",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!649edd71072546754b7456203b6a33aa",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "DC1",
            "external_ip": "5.29.231.235",
            "os": {
                "type": "Windows",
                "distribution": "Server 2016",
                "is_windows_server": true,
                "build": "14393",
                "os_str": "windowswindows server 2016",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 11:41:19",
            "first_fetch_time": "2020-05-18 11:54:24",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2018-08-22 15:32:44",
            "pretty_id": "AX-0",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 11:54:24",
            "network_interfaces": [
                {
                    "ips_raw": [
                        3232240665
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "mac": "00:0C:29:C6:95:5A",
                    "ips": [
                        "192.168.20.25"
                    ]
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device0",
            "system_product_name": "VMware Virtual Platform"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Phoenix Technologies LTD",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!fef6f12a62d34d8267516e95dbe50db6",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "DC2",
            "external_ip": "5.29.231.235",
            "os": {
                "type": "Windows",
                "distribution": "Server 2016",
                "is_windows_server": true,
                "build": "14393",
                "os_str": "windowswindows server 2016",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 11:38:33",
            "first_fetch_time": "2020-05-18 11:54:24",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2018-08-22 15:32:36",
            "pretty_id": "AX-1",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 11:54:24",
            "network_interfaces": [
                {
                    "ips_raw": [
                        3232240677
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "mac": "00:0C:29:81:6C:4A",
                    "ips": [
                        "192.168.20.37"
                    ]
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device1",
            "system_product_name": "VMware Virtual Platform"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Phoenix Technologies LTD",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!0dc44dcd8b664bfa6363e52365b3086a",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "DC4",
            "external_ip": "5.29.231.235",
            "os": {
                "type": "Windows",
                "distribution": "Server 2012",
                "is_windows_server": true,
                "build": "9600",
                "os_str": "windowswindows server 2012 r2",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 11:28:15",
            "first_fetch_time": "2020-05-18 11:54:24",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2018-08-22 15:32:36",
            "pretty_id": "AX-2",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 11:54:24",
            "network_interfaces": [
                {
                    "ips_raw": [
                        3232240657
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "mac": "00:0C:29:B6:DA:46",
                    "ips": [
                        "192.168.20.17"
                    ]
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device2",
            "system_product_name": "VMware Virtual Platform"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Amazon EC2",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!9e3686cbd686451c70f86aa4177a40fa",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "DCNY1",
            "external_ip": "18.220.31.78",
            "os": {
                "type": "Windows",
                "distribution": "Server 2016",
                "is_windows_server": true,
                "build": "14393",
                "os_str": "windowswindows server 2016",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 11:17:29",
            "first_fetch_time": "2020-05-18 11:54:24",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2018-08-22 15:31:51",
            "pretty_id": "AX-3",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 11:54:24",
            "network_interfaces": [
                {
                    "ips_raw": [
                        167772771
                    ],
                    "ips": [
                        "10.0.2.99"
                    ],
                    "mac": "06:80:99:50:D3:5E"
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device3",
            "system_product_name": "m5.xlarge"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Xen",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!5c0f1167cf93461478557908640b2bc4",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "EC2AMAZ-61GTBER",
            "external_ip": "18.220.31.78",
            "os": {
                "type": "Windows",
                "distribution": "Server 2016",
                "is_windows_server": true,
                "build": "14393",
                "os_str": "windowswindows server 2016",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 11:48:51",
            "first_fetch_time": "2020-05-18 11:54:24",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2018-08-22 15:30:08",
            "pretty_id": "AX-4",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 11:54:24",
            "network_interfaces": [
                {
                    "ips_raw": [
                        167772794
                    ],
                    "ips": [
                        "10.0.2.122"
                    ],
                    "mac": "06:D0:F5:79:4C:D0"
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device4",
            "system_product_name": "HVM domU"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Xen",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!60db0d1ddf09495a659100d303eeb6eb",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "EC2AMAZ-V8E9DHF",
            "external_ip": "18.220.31.78",
            "os": {
                "type": "Windows",
                "distribution": "Server 2016",
                "is_windows_server": true,
                "build": "14393",
                "os_str": "windowswindows server 2016",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 11:45:39",
            "first_fetch_time": "2020-05-18 11:54:24",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2020-04-21 09:50:26",
            "pretty_id": "AX-5",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 11:54:24",
            "network_interfaces": [
                {
                    "ips_raw": [
                        167772850
                    ],
                    "ips": [
                        "10.0.2.178"
                    ],
                    "mac": "06:DE:D4:0F:B4:18"
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device5",
            "system_product_name": "HVM domU"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Xen",
            "cs_agent_version": "5.24.10609.0",
            "quick_id": "crowd_strike_adapter_0!dc52b1f1a77f459779c028754745703e",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "WIN-76F9735PMOJ",
            "external_ip": "18.220.31.78",
            "os": {
                "type": "Windows",
                "distribution": "Server 2012",
                "is_windows_server": true,
                "build": "9600",
                "os_str": "windowswindows server 2012 r2",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 12:07:29",
            "first_fetch_time": "2020-05-18 12:09:14",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2018-08-22 15:30:09",
            "pretty_id": "AX-6",
            "agent_versions": [
                {
                    "agent_version": "5.24.10609.0",
                    "agent_version_raw": "000000005000000240001060900000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 12:09:14",
            "network_interfaces": [
                {
                    "ips_raw": [
                        167772792
                    ],
                    "ips": [
                        "10.0.2.120"
                    ],
                    "mac": "06:37:53:6E:A2:9C"
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device6",
            "system_product_name": "HVM domU"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Xen",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!8a04543f31fe4439718dc3dbb18ebd2e",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "WIN-D14VSGS3C0G",
            "external_ip": "18.220.31.78",
            "os": {
                "type": "Windows",
                "distribution": "Server 2012",
                "is_windows_server": true,
                "build": "9600",
                "os_str": "windowswindows server 2012 r2",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 11:47:58",
            "first_fetch_time": "2020-05-18 12:09:14",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2020-05-11 00:53:31",
            "pretty_id": "AX-7",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 12:09:14",
            "network_interfaces": [
                {
                    "ips_raw": [
                        2886795265
                    ],
                    "ips": [
                        "172.17.0.1"
                    ],
                    "mac": "02:60:5E:01:05:01"
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device7",
            "system_product_name": "HVM domU"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Xen",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!e688ef3e2c544c6f691fc900c4f17cef",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "WIN-QM01NAC82NR",
            "external_ip": "18.220.31.78",
            "os": {
                "type": "Windows",
                "distribution": "Server 2012",
                "is_windows_server": true,
                "build": "9200",
                "os_str": "windowswindows server 2012",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 11:42:09",
            "first_fetch_time": "2020-05-18 12:09:14",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2018-08-22 15:30:00",
            "pretty_id": "AX-8",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 12:09:14",
            "network_interfaces": [
                {
                    "ips_raw": [
                        167772926
                    ],
                    "ips": [
                        "10.0.2.254"
                    ],
                    "mac": "06:83:2D:7B:2B:4A"
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device8",
            "system_product_name": "HVM domU"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Amazon EC2",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!62258ee795e9457fa09e8fbb6a63b798",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "WIN-TV9UBKLP1KN",
            "external_ip": "18.220.31.78",
            "os": {
                "type": "Windows",
                "distribution": "Server 2012",
                "is_windows_server": true,
                "build": "9600",
                "os_str": "windowswindows server 2012 r2",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestSecDomain.test",
            "last_seen": "2020-05-18 12:04:54",
            "first_fetch_time": "2020-05-18 12:09:14",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2020-03-15 11:22:32",
            "pretty_id": "AX-9",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 12:09:14",
            "network_interfaces": [
                {
                    "ips_raw": [
                        167830793
                    ],
                    "ips": [
                        "10.0.229.9"
                    ],
                    "mac": "06:46:E2:F5:C5:68"
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device9",
            "system_product_name": "m5.xlarge"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Phoenix Technologies LTD",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!9c922b85705c41337f87d8a53d20840d",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "WINDOWS8",
            "external_ip": "5.29.231.235",
            "os": {
                "type": "Windows",
                "distribution": "8.1",
                "is_windows_server": false,
                "build": "9600",
                "os_str": "windowswindows 8.1",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 12:06:46",
            "first_fetch_time": "2020-05-18 12:09:15",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2018-08-22 15:31:57",
            "pretty_id": "AX-10",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 12:09:15",
            "network_interfaces": [
                {
                    "ips_raw": [
                        3232240649
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "mac": "00:0C:29:80:0E:60",
                    "ips": [
                        "192.168.20.9"
                    ]
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device10",
            "system_product_name": "VMware Virtual Platform"
        },
        {
            "connected_devices": [],
            "device_manufacturer": "Xen",
            "cs_agent_version": "5.30.11206.0",
            "quick_id": "crowd_strike_adapter_0!4ea61e4290b9438f6facb5d25476a5eb",
            "client_used": "api.crowdstrike.com_ca5474ed12ae450eb6f16e08e774a746",
            "type": "entitydata",
            "plugin_type": "Adapter",
            "hostname": "22AD",
            "external_ip": "18.220.31.78",
            "os": {
                "type": "Windows",
                "distribution": "Server 2012",
                "is_windows_server": true,
                "build": "9600",
                "os_str": "windowswindows server 2012 r2",
                "major": 0,
                "minor": 0
            },
            "accurate_for_datetime": "2020-05-18 12:12:45",
            "domain": "TestDomain.test",
            "last_seen": "2020-05-18 11:56:54",
            "first_fetch_time": "2020-05-18 12:11:53",
            "adapter_properties": [
                "Agent",
                "Endpoint_Protection_Platform"
            ],
            "first_seen": "2018-08-22 15:30:12",
            "pretty_id": "AX-11",
            "agent_versions": [
                {
                    "agent_version": "5.30.11206.0",
                    "agent_version_raw": "000000005000000300001120600000000",
                    "agent_status": "normal",
                    "adapter_name": "CrowdStrike Agent"
                }
            ],
            "plugin_name": "crowd_strike_adapter",
            "fetch_time": "2020-05-18 12:11:53",
            "network_interfaces": [
                {
                    "ips_raw": [
                        167830298
                    ],
                    "ips": [
                        "10.0.227.26"
                    ],
                    "mac": "06:75:D9:93:EE:68"
                }
            ],
            "plugin_unique_name": "crowd_strike_adapter_0",
            "groups": [],
            "id": "device11",
            "system_product_name": "HVM domU"
        }
    ],
    "raw_fields": [],
    "additional_schema": [
        {
            "title": "External IP",
            "type": "string",
            "name": "external_ip"
        },
        {
            "title": "Groups",
            "type": "array",
            "name": "groups",
            "items": {
                "type": "array",
                "items": [
                    {
                        "title": "Created By",
                        "type": "string",
                        "name": "created_by"
                    },
                    {
                        "title": "Created Time",
                        "type": "string",
                        "name": "created_timestamp",
                        "format": "date-time"
                    },
                    {
                        "title": "Description",
                        "type": "string",
                        "name": "description"
                    },
                    {
                        "title": "Group Type",
                        "type": "string",
                        "name": "group_type"
                    },
                    {
                        "title": "Id",
                        "type": "string",
                        "name": "id"
                    },
                    {
                        "title": "Modified By",
                        "type": "string",
                        "name": "modified_by"
                    },
                    {
                        "title": "Modified Time",
                        "type": "string",
                        "name": "modified_time",
                        "format": "date-time"
                    },
                    {
                        "title": "Name",
                        "type": "string",
                        "name": "name"
                    }
                ]
            }
        },
        {
            "branched": true,
            "title": "Groups: Created By",
            "name": "groups.created_by",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Groups: Created Time",
            "name": "groups.created_timestamp",
            "type": "string",
            "format": "date-time"
        },
        {
            "branched": true,
            "title": "Groups: Description",
            "name": "groups.description",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Groups: Group Type",
            "name": "groups.group_type",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Groups: Id",
            "name": "groups.id",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Groups: Modified By",
            "name": "groups.modified_by",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Groups: Modified Time",
            "name": "groups.modified_time",
            "type": "string",
            "format": "date-time"
        },
        {
            "branched": true,
            "title": "Groups: Name",
            "name": "groups.name",
            "type": "string"
        },
        {
            "title": "CrowdStrike Agent Version",
            "type": "string",
            "name": "cs_agent_version"
        },
        {
            "title": "System Product Name",
            "type": "string",
            "name": "system_product_name"
        },
        {
            "title": "Host Name",
            "type": "string",
            "name": "hostname"
        },
        {
            "title": "First Seen",
            "type": "string",
            "name": "first_seen",
            "format": "date-time"
        },
        {
            "title": "Last Seen",
            "type": "string",
            "name": "last_seen",
            "format": "date-time"
        },
        {
            "title": "Fetch Time",
            "type": "string",
            "name": "fetch_time",
            "format": "date-time"
        },
        {
            "title": "First Fetch Time",
            "type": "string",
            "name": "first_fetch_time",
            "format": "date-time"
        },
        {
            "title": "Network Interfaces",
            "type": "array",
            "name": "network_interfaces",
            "format": "table",
            "items": {
                "type": "array",
                "items": [
                    {
                        "title": "Iface Name",
                        "type": "string",
                        "name": "name"
                    },
                    {
                        "title": "MAC",
                        "type": "string",
                        "name": "mac"
                    },
                    {
                        "title": "Manufacturer",
                        "type": "string",
                        "name": "manufacturer"
                    },
                    {
                        "title": "IPs",
                        "type": "array",
                        "name": "ips",
                        "format": "ip",
                        "items": {
                            "type": "string",
                            "format": "ip"
                        }
                    },
                    {
                        "description": "A list of subnets in ip format, that correspond the IPs",
                        "type": "array",
                        "title": "Subnets",
                        "format": "subnet",
                        "name": "subnets",
                        "items": {
                            "type": "string",
                            "format": "subnet"
                        }
                    },
                    {
                        "description": "A list of vlans in this interface",
                        "title": "Vlans",
                        "name": "vlan_list",
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": [
                                {
                                    "title": "Vlan Name",
                                    "type": "string",
                                    "name": "name"
                                },
                                {
                                    "title": "Tag ID",
                                    "type": "integer",
                                    "name": "tagid"
                                },
                                {
                                    "title": "Vlan Tagness",
                                    "type": "string",
                                    "name": "tagness",
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ]
                                }
                            ]
                        }
                    },
                    {
                        "branched": true,
                        "title": "Vlans: Vlan Name",
                        "name": "vlan_list.name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Vlans: Tag ID",
                        "name": "vlan_list.tagid",
                        "type": "integer"
                    },
                    {
                        "branched": true,
                        "title": "Vlans: Vlan Tagness",
                        "name": "vlan_list.tagness",
                        "type": "string",
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ]
                    },
                    {
                        "title": "Operational Status",
                        "type": "string",
                        "name": "operational_status",
                        "enum": [
                            "Up",
                            "Down",
                            "Testing",
                            "Unknown",
                            "Dormant",
                            "Nonpresent",
                            "LowerLayerDown"
                        ]
                    },
                    {
                        "title": "Admin Status",
                        "type": "string",
                        "name": "admin_status",
                        "enum": [
                            "Up",
                            "Down",
                            "Testing"
                        ]
                    },
                    {
                        "description": "Interface max speed per Second",
                        "title": "Interface Speed",
                        "name": "speed",
                        "type": "string"
                    },
                    {
                        "title": "Port Type",
                        "type": "string",
                        "name": "port_type",
                        "enum": [
                            "Access",
                            "Trunk"
                        ]
                    },
                    {
                        "description": "Interface Maximum transmission unit",
                        "title": "MTU",
                        "name": "mtu",
                        "type": "string"
                    },
                    {
                        "title": "Gateway",
                        "type": "string",
                        "name": "gateway"
                    },
                    {
                        "title": "Port",
                        "type": "string",
                        "name": "port"
                    }
                ]
            }
        },
        {
            "branched": true,
            "title": "Network Interfaces: Iface Name",
            "name": "network_interfaces.name",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Network Interfaces: MAC",
            "name": "network_interfaces.mac",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Network Interfaces: Manufacturer",
            "name": "network_interfaces.manufacturer",
            "type": "string"
        },
        {
            "title": "Network Interfaces: IPs",
            "type": "array",
            "name": "network_interfaces.ips",
            "format": "ip",
            "items": {
                "type": "string",
                "format": "ip"
            }
        },
        {
            "description": "A list of subnets in ip format, that correspond the IPs",
            "type": "array",
            "title": "Network Interfaces: Subnets",
            "format": "subnet",
            "name": "network_interfaces.subnets",
            "items": {
                "type": "string",
                "format": "subnet"
            }
        },
        {
            "description": "A list of vlans in this interface",
            "title": "Network Interfaces: Vlans",
            "name": "network_interfaces.vlan_list",
            "type": "array",
            "items": {
                "type": "array",
                "items": [
                    {
                        "title": "Vlan Name",
                        "type": "string",
                        "name": "name"
                    },
                    {
                        "title": "Tag ID",
                        "type": "integer",
                        "name": "tagid"
                    },
                    {
                        "title": "Vlan Tagness",
                        "type": "string",
                        "name": "tagness",
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ]
                    }
                ]
            }
        },
        {
            "branched": true,
            "title": "Network Interfaces: Vlans: Vlan Name",
            "name": "network_interfaces.vlan_list.name",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Network Interfaces: Vlans: Tag ID",
            "name": "network_interfaces.vlan_list.tagid",
            "type": "integer"
        },
        {
            "branched": true,
            "title": "Network Interfaces: Vlans: Vlan Tagness",
            "name": "network_interfaces.vlan_list.tagness",
            "type": "string",
            "enum": [
                "Tagged",
                "Untagged"
            ]
        },
        {
            "branched": true,
            "title": "Network Interfaces: Operational Status",
            "name": "network_interfaces.operational_status",
            "type": "string",
            "enum": [
                "Up",
                "Down",
                "Testing",
                "Unknown",
                "Dormant",
                "Nonpresent",
                "LowerLayerDown"
            ]
        },
        {
            "branched": true,
            "title": "Network Interfaces: Admin Status",
            "name": "network_interfaces.admin_status",
            "type": "string",
            "enum": [
                "Up",
                "Down",
                "Testing"
            ]
        },
        {
            "branched": true,
            "title": "Network Interfaces: Interface Speed",
            "name": "network_interfaces.speed",
            "type": "string",
            "description": "Interface max speed per Second"
        },
        {
            "branched": true,
            "title": "Network Interfaces: Port Type",
            "name": "network_interfaces.port_type",
            "type": "string",
            "enum": [
                "Access",
                "Trunk"
            ]
        },
        {
            "branched": true,
            "title": "Network Interfaces: MTU",
            "name": "network_interfaces.mtu",
            "type": "string",
            "description": "Interface Maximum transmission unit"
        },
        {
            "branched": true,
            "title": "Network Interfaces: Gateway",
            "name": "network_interfaces.gateway",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Network Interfaces: Port",
            "name": "network_interfaces.port",
            "type": "string"
        },
        {
            "title": "OS: Type",
            "type": "string",
            "name": "os.type",
            "enum": [
                "Windows",
                "Linux",
                "OS X",
                "iOS",
                "AirOS",
                "Android",
                "FreeBSD",
                "VMWare",
                "Cisco",
                "Mikrotik",
                "VxWorks",
                "PanOS",
                "F5 Networks Big-IP",
                "Solaris",
                "AIX",
                "Printer",
                "PlayStation",
                "Check Point",
                "Arista",
                "Netscaler"
            ]
        },
        {
            "title": "OS: Distribution",
            "type": "string",
            "name": "os.distribution"
        },
        {
            "title": "OS: Is Windows Server",
            "type": "bool",
            "name": "os.is_windows_server"
        },
        {
            "title": "OS: Full OS String",
            "type": "string",
            "name": "os.os_str"
        },
        {
            "title": "OS: Bitness",
            "type": "integer",
            "name": "os.bitness",
            "enum": [
                32,
                64
            ]
        },
        {
            "title": "OS: Service Pack",
            "type": "string",
            "name": "os.sp"
        },
        {
            "title": "OS: Install Date",
            "type": "string",
            "name": "os.install_date",
            "format": "date-time"
        },
        {
            "title": "OS: Kernel Version",
            "type": "string",
            "name": "os.kernel_version"
        },
        {
            "title": "OS: Code name",
            "type": "string",
            "name": "os.codename"
        },
        {
            "title": "OS: Major",
            "type": "integer",
            "name": "os.major"
        },
        {
            "title": "OS: Minor",
            "type": "integer",
            "name": "os.minor"
        },
        {
            "title": "OS: Build",
            "type": "string",
            "name": "os.build"
        },
        {
            "title": "OS: Serial",
            "type": "string",
            "name": "os.serial"
        },
        {
            "title": "Connected Devices",
            "type": "array",
            "name": "connected_devices",
            "format": "table",
            "items": {
                "type": "array",
                "items": [
                    {
                        "title": "Remote Device Name",
                        "type": "string",
                        "name": "remote_name"
                    },
                    {
                        "title": "Local Interface",
                        "type": "array",
                        "name": "local_ifaces",
                        "items": {
                            "type": "array",
                            "items": [
                                {
                                    "title": "Iface Name",
                                    "type": "string",
                                    "name": "name"
                                },
                                {
                                    "title": "MAC",
                                    "type": "string",
                                    "name": "mac"
                                },
                                {
                                    "title": "Manufacturer",
                                    "type": "string",
                                    "name": "manufacturer"
                                },
                                {
                                    "title": "IPs",
                                    "type": "array",
                                    "name": "ips",
                                    "format": "ip",
                                    "items": {
                                        "type": "string",
                                        "format": "ip"
                                    }
                                },
                                {
                                    "description": "A list of subnets in ip format, that correspond the IPs",
                                    "type": "array",
                                    "title": "Subnets",
                                    "format": "subnet",
                                    "name": "subnets",
                                    "items": {
                                        "type": "string",
                                        "format": "subnet"
                                    }
                                },
                                {
                                    "description": "A list of vlans in this interface",
                                    "title": "Vlans",
                                    "name": "vlan_list",
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "items": [
                                            {
                                                "title": "Vlan Name",
                                                "type": "string",
                                                "name": "name"
                                            },
                                            {
                                                "title": "Tag ID",
                                                "type": "integer",
                                                "name": "tagid"
                                            },
                                            {
                                                "title": "Vlan Tagness",
                                                "type": "string",
                                                "name": "tagness",
                                                "enum": [
                                                    "Tagged",
                                                    "Untagged"
                                                ]
                                            }
                                        ]
                                    }
                                },
                                {
                                    "branched": true,
                                    "title": "Vlans: Vlan Name",
                                    "name": "vlan_list.name",
                                    "type": "string"
                                },
                                {
                                    "branched": true,
                                    "title": "Vlans: Tag ID",
                                    "name": "vlan_list.tagid",
                                    "type": "integer"
                                },
                                {
                                    "branched": true,
                                    "title": "Vlans: Vlan Tagness",
                                    "name": "vlan_list.tagness",
                                    "type": "string",
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ]
                                },
                                {
                                    "title": "Operational Status",
                                    "type": "string",
                                    "name": "operational_status",
                                    "enum": [
                                        "Up",
                                        "Down",
                                        "Testing",
                                        "Unknown",
                                        "Dormant",
                                        "Nonpresent",
                                        "LowerLayerDown"
                                    ]
                                },
                                {
                                    "title": "Admin Status",
                                    "type": "string",
                                    "name": "admin_status",
                                    "enum": [
                                        "Up",
                                        "Down",
                                        "Testing"
                                    ]
                                },
                                {
                                    "description": "Interface max speed per Second",
                                    "title": "Interface Speed",
                                    "name": "speed",
                                    "type": "string"
                                },
                                {
                                    "title": "Port Type",
                                    "type": "string",
                                    "name": "port_type",
                                    "enum": [
                                        "Access",
                                        "Trunk"
                                    ]
                                },
                                {
                                    "description": "Interface Maximum transmission unit",
                                    "title": "MTU",
                                    "name": "mtu",
                                    "type": "string"
                                },
                                {
                                    "title": "Gateway",
                                    "type": "string",
                                    "name": "gateway"
                                },
                                {
                                    "title": "Port",
                                    "type": "string",
                                    "name": "port"
                                }
                            ]
                        }
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Iface Name",
                        "name": "local_ifaces.name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: MAC",
                        "name": "local_ifaces.mac",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Manufacturer",
                        "name": "local_ifaces.manufacturer",
                        "type": "string"
                    },
                    {
                        "title": "Local Interface: IPs",
                        "type": "array",
                        "name": "local_ifaces.ips",
                        "format": "ip",
                        "items": {
                            "type": "string",
                            "format": "ip"
                        }
                    },
                    {
                        "description": "A list of subnets in ip format, that correspond the IPs",
                        "type": "array",
                        "title": "Local Interface: Subnets",
                        "format": "subnet",
                        "name": "local_ifaces.subnets",
                        "items": {
                            "type": "string",
                            "format": "subnet"
                        }
                    },
                    {
                        "description": "A list of vlans in this interface",
                        "title": "Local Interface: Vlans",
                        "name": "local_ifaces.vlan_list",
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": [
                                {
                                    "title": "Vlan Name",
                                    "type": "string",
                                    "name": "name"
                                },
                                {
                                    "title": "Tag ID",
                                    "type": "integer",
                                    "name": "tagid"
                                },
                                {
                                    "title": "Vlan Tagness",
                                    "type": "string",
                                    "name": "tagness",
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ]
                                }
                            ]
                        }
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Vlans: Vlan Name",
                        "name": "local_ifaces.vlan_list.name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Vlans: Tag ID",
                        "name": "local_ifaces.vlan_list.tagid",
                        "type": "integer"
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Vlans: Vlan Tagness",
                        "name": "local_ifaces.vlan_list.tagness",
                        "type": "string",
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ]
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Operational Status",
                        "name": "local_ifaces.operational_status",
                        "type": "string",
                        "enum": [
                            "Up",
                            "Down",
                            "Testing",
                            "Unknown",
                            "Dormant",
                            "Nonpresent",
                            "LowerLayerDown"
                        ]
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Admin Status",
                        "name": "local_ifaces.admin_status",
                        "type": "string",
                        "enum": [
                            "Up",
                            "Down",
                            "Testing"
                        ]
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Interface Speed",
                        "name": "local_ifaces.speed",
                        "type": "string",
                        "description": "Interface max speed per Second"
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Port Type",
                        "name": "local_ifaces.port_type",
                        "type": "string",
                        "enum": [
                            "Access",
                            "Trunk"
                        ]
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: MTU",
                        "name": "local_ifaces.mtu",
                        "type": "string",
                        "description": "Interface Maximum transmission unit"
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Gateway",
                        "name": "local_ifaces.gateway",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Local Interface: Port",
                        "name": "local_ifaces.port",
                        "type": "string"
                    },
                    {
                        "title": "Remote Device Iface",
                        "type": "array",
                        "name": "remote_ifaces",
                        "items": {
                            "type": "array",
                            "items": [
                                {
                                    "title": "Iface Name",
                                    "type": "string",
                                    "name": "name"
                                },
                                {
                                    "title": "MAC",
                                    "type": "string",
                                    "name": "mac"
                                },
                                {
                                    "title": "Manufacturer",
                                    "type": "string",
                                    "name": "manufacturer"
                                },
                                {
                                    "title": "IPs",
                                    "type": "array",
                                    "name": "ips",
                                    "format": "ip",
                                    "items": {
                                        "type": "string",
                                        "format": "ip"
                                    }
                                },
                                {
                                    "description": "A list of subnets in ip format, that correspond the IPs",
                                    "type": "array",
                                    "title": "Subnets",
                                    "format": "subnet",
                                    "name": "subnets",
                                    "items": {
                                        "type": "string",
                                        "format": "subnet"
                                    }
                                },
                                {
                                    "description": "A list of vlans in this interface",
                                    "title": "Vlans",
                                    "name": "vlan_list",
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "items": [
                                            {
                                                "title": "Vlan Name",
                                                "type": "string",
                                                "name": "name"
                                            },
                                            {
                                                "title": "Tag ID",
                                                "type": "integer",
                                                "name": "tagid"
                                            },
                                            {
                                                "title": "Vlan Tagness",
                                                "type": "string",
                                                "name": "tagness",
                                                "enum": [
                                                    "Tagged",
                                                    "Untagged"
                                                ]
                                            }
                                        ]
                                    }
                                },
                                {
                                    "branched": true,
                                    "title": "Vlans: Vlan Name",
                                    "name": "vlan_list.name",
                                    "type": "string"
                                },
                                {
                                    "branched": true,
                                    "title": "Vlans: Tag ID",
                                    "name": "vlan_list.tagid",
                                    "type": "integer"
                                },
                                {
                                    "branched": true,
                                    "title": "Vlans: Vlan Tagness",
                                    "name": "vlan_list.tagness",
                                    "type": "string",
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ]
                                },
                                {
                                    "title": "Operational Status",
                                    "type": "string",
                                    "name": "operational_status",
                                    "enum": [
                                        "Up",
                                        "Down",
                                        "Testing",
                                        "Unknown",
                                        "Dormant",
                                        "Nonpresent",
                                        "LowerLayerDown"
                                    ]
                                },
                                {
                                    "title": "Admin Status",
                                    "type": "string",
                                    "name": "admin_status",
                                    "enum": [
                                        "Up",
                                        "Down",
                                        "Testing"
                                    ]
                                },
                                {
                                    "description": "Interface max speed per Second",
                                    "title": "Interface Speed",
                                    "name": "speed",
                                    "type": "string"
                                },
                                {
                                    "title": "Port Type",
                                    "type": "string",
                                    "name": "port_type",
                                    "enum": [
                                        "Access",
                                        "Trunk"
                                    ]
                                },
                                {
                                    "description": "Interface Maximum transmission unit",
                                    "title": "MTU",
                                    "name": "mtu",
                                    "type": "string"
                                },
                                {
                                    "title": "Gateway",
                                    "type": "string",
                                    "name": "gateway"
                                },
                                {
                                    "title": "Port",
                                    "type": "string",
                                    "name": "port"
                                }
                            ]
                        }
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Iface Name",
                        "name": "remote_ifaces.name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: MAC",
                        "name": "remote_ifaces.mac",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Manufacturer",
                        "name": "remote_ifaces.manufacturer",
                        "type": "string"
                    },
                    {
                        "title": "Remote Device Iface: IPs",
                        "type": "array",
                        "name": "remote_ifaces.ips",
                        "format": "ip",
                        "items": {
                            "type": "string",
                            "format": "ip"
                        }
                    },
                    {
                        "description": "A list of subnets in ip format, that correspond the IPs",
                        "type": "array",
                        "title": "Remote Device Iface: Subnets",
                        "format": "subnet",
                        "name": "remote_ifaces.subnets",
                        "items": {
                            "type": "string",
                            "format": "subnet"
                        }
                    },
                    {
                        "description": "A list of vlans in this interface",
                        "title": "Remote Device Iface: Vlans",
                        "name": "remote_ifaces.vlan_list",
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": [
                                {
                                    "title": "Vlan Name",
                                    "type": "string",
                                    "name": "name"
                                },
                                {
                                    "title": "Tag ID",
                                    "type": "integer",
                                    "name": "tagid"
                                },
                                {
                                    "title": "Vlan Tagness",
                                    "type": "string",
                                    "name": "tagness",
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ]
                                }
                            ]
                        }
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Vlans: Vlan Name",
                        "name": "remote_ifaces.vlan_list.name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Vlans: Tag ID",
                        "name": "remote_ifaces.vlan_list.tagid",
                        "type": "integer"
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Vlans: Vlan Tagness",
                        "name": "remote_ifaces.vlan_list.tagness",
                        "type": "string",
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ]
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Operational Status",
                        "name": "remote_ifaces.operational_status",
                        "type": "string",
                        "enum": [
                            "Up",
                            "Down",
                            "Testing",
                            "Unknown",
                            "Dormant",
                            "Nonpresent",
                            "LowerLayerDown"
                        ]
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Admin Status",
                        "name": "remote_ifaces.admin_status",
                        "type": "string",
                        "enum": [
                            "Up",
                            "Down",
                            "Testing"
                        ]
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Interface Speed",
                        "name": "remote_ifaces.speed",
                        "type": "string",
                        "description": "Interface max speed per Second"
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Port Type",
                        "name": "remote_ifaces.port_type",
                        "type": "string",
                        "enum": [
                            "Access",
                            "Trunk"
                        ]
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: MTU",
                        "name": "remote_ifaces.mtu",
                        "type": "string",
                        "description": "Interface Maximum transmission unit"
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Gateway",
                        "name": "remote_ifaces.gateway",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Remote Device Iface: Port",
                        "name": "remote_ifaces.port",
                        "type": "string"
                    },
                    {
                        "title": "Connection Type",
                        "type": "string",
                        "name": "connection_type",
                        "enum": [
                            "Direct",
                            "Indirect"
                        ]
                    }
                ]
            }
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Name",
            "name": "connected_devices.remote_name",
            "type": "string"
        },
        {
            "title": "Connected Devices: Local Interface",
            "type": "array",
            "name": "connected_devices.local_ifaces",
            "items": {
                "type": "array",
                "items": [
                    {
                        "title": "Iface Name",
                        "type": "string",
                        "name": "name"
                    },
                    {
                        "title": "MAC",
                        "type": "string",
                        "name": "mac"
                    },
                    {
                        "title": "Manufacturer",
                        "type": "string",
                        "name": "manufacturer"
                    },
                    {
                        "title": "IPs",
                        "type": "array",
                        "name": "ips",
                        "format": "ip",
                        "items": {
                            "type": "string",
                            "format": "ip"
                        }
                    },
                    {
                        "description": "A list of subnets in ip format, that correspond the IPs",
                        "type": "array",
                        "title": "Subnets",
                        "format": "subnet",
                        "name": "subnets",
                        "items": {
                            "type": "string",
                            "format": "subnet"
                        }
                    },
                    {
                        "description": "A list of vlans in this interface",
                        "title": "Vlans",
                        "name": "vlan_list",
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": [
                                {
                                    "title": "Vlan Name",
                                    "type": "string",
                                    "name": "name"
                                },
                                {
                                    "title": "Tag ID",
                                    "type": "integer",
                                    "name": "tagid"
                                },
                                {
                                    "title": "Vlan Tagness",
                                    "type": "string",
                                    "name": "tagness",
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ]
                                }
                            ]
                        }
                    },
                    {
                        "branched": true,
                        "title": "Vlans: Vlan Name",
                        "name": "vlan_list.name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Vlans: Tag ID",
                        "name": "vlan_list.tagid",
                        "type": "integer"
                    },
                    {
                        "branched": true,
                        "title": "Vlans: Vlan Tagness",
                        "name": "vlan_list.tagness",
                        "type": "string",
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ]
                    },
                    {
                        "title": "Operational Status",
                        "type": "string",
                        "name": "operational_status",
                        "enum": [
                            "Up",
                            "Down",
                            "Testing",
                            "Unknown",
                            "Dormant",
                            "Nonpresent",
                            "LowerLayerDown"
                        ]
                    },
                    {
                        "title": "Admin Status",
                        "type": "string",
                        "name": "admin_status",
                        "enum": [
                            "Up",
                            "Down",
                            "Testing"
                        ]
                    },
                    {
                        "description": "Interface max speed per Second",
                        "title": "Interface Speed",
                        "name": "speed",
                        "type": "string"
                    },
                    {
                        "title": "Port Type",
                        "type": "string",
                        "name": "port_type",
                        "enum": [
                            "Access",
                            "Trunk"
                        ]
                    },
                    {
                        "description": "Interface Maximum transmission unit",
                        "title": "MTU",
                        "name": "mtu",
                        "type": "string"
                    },
                    {
                        "title": "Gateway",
                        "type": "string",
                        "name": "gateway"
                    },
                    {
                        "title": "Port",
                        "type": "string",
                        "name": "port"
                    }
                ]
            }
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Iface Name",
            "name": "connected_devices.local_ifaces.name",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: MAC",
            "name": "connected_devices.local_ifaces.mac",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Manufacturer",
            "name": "connected_devices.local_ifaces.manufacturer",
            "type": "string"
        },
        {
            "title": "Connected Devices: Local Interface: IPs",
            "type": "array",
            "name": "connected_devices.local_ifaces.ips",
            "format": "ip",
            "items": {
                "type": "string",
                "format": "ip"
            }
        },
        {
            "description": "A list of subnets in ip format, that correspond the IPs",
            "type": "array",
            "title": "Connected Devices: Local Interface: Subnets",
            "format": "subnet",
            "name": "connected_devices.local_ifaces.subnets",
            "items": {
                "type": "string",
                "format": "subnet"
            }
        },
        {
            "description": "A list of vlans in this interface",
            "title": "Connected Devices: Local Interface: Vlans",
            "name": "connected_devices.local_ifaces.vlan_list",
            "type": "array",
            "items": {
                "type": "array",
                "items": [
                    {
                        "title": "Vlan Name",
                        "type": "string",
                        "name": "name"
                    },
                    {
                        "title": "Tag ID",
                        "type": "integer",
                        "name": "tagid"
                    },
                    {
                        "title": "Vlan Tagness",
                        "type": "string",
                        "name": "tagness",
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ]
                    }
                ]
            }
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Vlans: Vlan Name",
            "name": "connected_devices.local_ifaces.vlan_list.name",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Vlans: Tag ID",
            "name": "connected_devices.local_ifaces.vlan_list.tagid",
            "type": "integer"
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Vlans: Vlan Tagness",
            "name": "connected_devices.local_ifaces.vlan_list.tagness",
            "type": "string",
            "enum": [
                "Tagged",
                "Untagged"
            ]
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Operational Status",
            "name": "connected_devices.local_ifaces.operational_status",
            "type": "string",
            "enum": [
                "Up",
                "Down",
                "Testing",
                "Unknown",
                "Dormant",
                "Nonpresent",
                "LowerLayerDown"
            ]
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Admin Status",
            "name": "connected_devices.local_ifaces.admin_status",
            "type": "string",
            "enum": [
                "Up",
                "Down",
                "Testing"
            ]
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Interface Speed",
            "name": "connected_devices.local_ifaces.speed",
            "type": "string",
            "description": "Interface max speed per Second"
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Port Type",
            "name": "connected_devices.local_ifaces.port_type",
            "type": "string",
            "enum": [
                "Access",
                "Trunk"
            ]
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: MTU",
            "name": "connected_devices.local_ifaces.mtu",
            "type": "string",
            "description": "Interface Maximum transmission unit"
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Gateway",
            "name": "connected_devices.local_ifaces.gateway",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Connected Devices: Local Interface: Port",
            "name": "connected_devices.local_ifaces.port",
            "type": "string"
        },
        {
            "title": "Connected Devices: Remote Device Iface",
            "type": "array",
            "name": "connected_devices.remote_ifaces",
            "items": {
                "type": "array",
                "items": [
                    {
                        "title": "Iface Name",
                        "type": "string",
                        "name": "name"
                    },
                    {
                        "title": "MAC",
                        "type": "string",
                        "name": "mac"
                    },
                    {
                        "title": "Manufacturer",
                        "type": "string",
                        "name": "manufacturer"
                    },
                    {
                        "title": "IPs",
                        "type": "array",
                        "name": "ips",
                        "format": "ip",
                        "items": {
                            "type": "string",
                            "format": "ip"
                        }
                    },
                    {
                        "description": "A list of subnets in ip format, that correspond the IPs",
                        "type": "array",
                        "title": "Subnets",
                        "format": "subnet",
                        "name": "subnets",
                        "items": {
                            "type": "string",
                            "format": "subnet"
                        }
                    },
                    {
                        "description": "A list of vlans in this interface",
                        "title": "Vlans",
                        "name": "vlan_list",
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": [
                                {
                                    "title": "Vlan Name",
                                    "type": "string",
                                    "name": "name"
                                },
                                {
                                    "title": "Tag ID",
                                    "type": "integer",
                                    "name": "tagid"
                                },
                                {
                                    "title": "Vlan Tagness",
                                    "type": "string",
                                    "name": "tagness",
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ]
                                }
                            ]
                        }
                    },
                    {
                        "branched": true,
                        "title": "Vlans: Vlan Name",
                        "name": "vlan_list.name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "title": "Vlans: Tag ID",
                        "name": "vlan_list.tagid",
                        "type": "integer"
                    },
                    {
                        "branched": true,
                        "title": "Vlans: Vlan Tagness",
                        "name": "vlan_list.tagness",
                        "type": "string",
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ]
                    },
                    {
                        "title": "Operational Status",
                        "type": "string",
                        "name": "operational_status",
                        "enum": [
                            "Up",
                            "Down",
                            "Testing",
                            "Unknown",
                            "Dormant",
                            "Nonpresent",
                            "LowerLayerDown"
                        ]
                    },
                    {
                        "title": "Admin Status",
                        "type": "string",
                        "name": "admin_status",
                        "enum": [
                            "Up",
                            "Down",
                            "Testing"
                        ]
                    },
                    {
                        "description": "Interface max speed per Second",
                        "title": "Interface Speed",
                        "name": "speed",
                        "type": "string"
                    },
                    {
                        "title": "Port Type",
                        "type": "string",
                        "name": "port_type",
                        "enum": [
                            "Access",
                            "Trunk"
                        ]
                    },
                    {
                        "description": "Interface Maximum transmission unit",
                        "title": "MTU",
                        "name": "mtu",
                        "type": "string"
                    },
                    {
                        "title": "Gateway",
                        "type": "string",
                        "name": "gateway"
                    },
                    {
                        "title": "Port",
                        "type": "string",
                        "name": "port"
                    }
                ]
            }
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Iface Name",
            "name": "connected_devices.remote_ifaces.name",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: MAC",
            "name": "connected_devices.remote_ifaces.mac",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Manufacturer",
            "name": "connected_devices.remote_ifaces.manufacturer",
            "type": "string"
        },
        {
            "title": "Connected Devices: Remote Device Iface: IPs",
            "type": "array",
            "name": "connected_devices.remote_ifaces.ips",
            "format": "ip",
            "items": {
                "type": "string",
                "format": "ip"
            }
        },
        {
            "description": "A list of subnets in ip format, that correspond the IPs",
            "type": "array",
            "title": "Connected Devices: Remote Device Iface: Subnets",
            "format": "subnet",
            "name": "connected_devices.remote_ifaces.subnets",
            "items": {
                "type": "string",
                "format": "subnet"
            }
        },
        {
            "description": "A list of vlans in this interface",
            "title": "Connected Devices: Remote Device Iface: Vlans",
            "name": "connected_devices.remote_ifaces.vlan_list",
            "type": "array",
            "items": {
                "type": "array",
                "items": [
                    {
                        "title": "Vlan Name",
                        "type": "string",
                        "name": "name"
                    },
                    {
                        "title": "Tag ID",
                        "type": "integer",
                        "name": "tagid"
                    },
                    {
                        "title": "Vlan Tagness",
                        "type": "string",
                        "name": "tagness",
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ]
                    }
                ]
            }
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Vlans: Vlan Name",
            "name": "connected_devices.remote_ifaces.vlan_list.name",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Vlans: Tag ID",
            "name": "connected_devices.remote_ifaces.vlan_list.tagid",
            "type": "integer"
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Vlans: Vlan Tagness",
            "name": "connected_devices.remote_ifaces.vlan_list.tagness",
            "type": "string",
            "enum": [
                "Tagged",
                "Untagged"
            ]
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Operational Status",
            "name": "connected_devices.remote_ifaces.operational_status",
            "type": "string",
            "enum": [
                "Up",
                "Down",
                "Testing",
                "Unknown",
                "Dormant",
                "Nonpresent",
                "LowerLayerDown"
            ]
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Admin Status",
            "name": "connected_devices.remote_ifaces.admin_status",
            "type": "string",
            "enum": [
                "Up",
                "Down",
                "Testing"
            ]
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Interface Speed",
            "name": "connected_devices.remote_ifaces.speed",
            "type": "string",
            "description": "Interface max speed per Second"
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Port Type",
            "name": "connected_devices.remote_ifaces.port_type",
            "type": "string",
            "enum": [
                "Access",
                "Trunk"
            ]
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: MTU",
            "name": "connected_devices.remote_ifaces.mtu",
            "type": "string",
            "description": "Interface Maximum transmission unit"
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Gateway",
            "name": "connected_devices.remote_ifaces.gateway",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Connected Devices: Remote Device Iface: Port",
            "name": "connected_devices.remote_ifaces.port",
            "type": "string"
        },
        {
            "branched": true,
            "title": "Connected Devices: Connection Type",
            "name": "connected_devices.connection_type",
            "type": "string",
            "enum": [
                "Direct",
                "Indirect"
            ]
        },
        {
            "title": "ID",
            "type": "string",
            "name": "id"
        },
        {
            "title": "Domain",
            "type": "string",
            "name": "domain"
        },
        {
            "title": "Agent Versions",
            "type": "array",
            "name": "agent_versions",
            "format": "table",
            "items": {
                "type": "array",
                "items": [
                    {
                        "title": "Name",
                        "type": "string",
                        "name": "adapter_name",
                        "enum": [
                            "Alert Logic Agent",
                            "IBM BigFix Agent",
                            "CarbonBlack Defense Sensor",
                            "CarbonBlack Protection Sensor",
                            "CarbonBlack Response Sensor",
                            "Cisco AMP Connector",
                            "Cisco FMC Agent",
                            "Cisco Umbrella Agent",
                            "CloudPassage Daemon",
                            "Code42 Agent",
                            "CounterACT Agent",
                            "CrowdStrike Agent",
                            "Cylance Agent",
                            "Datadog Agent",
                            "Desktop Central Agent",
                            "Dropbox Client",
                            "Druva Client",
                            "Endgame Sensor",
                            "enSilo Agent",
                            "McAfee EPO Agent",
                            "FireEye HX Agent",
                            "Forcepoint Client",
                            "Imperva DAM Agent",
                            "JumpCloud Agent",
                            "Kaseya Agent",
                            "Lansweeper Agent",
                            "Minerva Labs Agent",
                            "MobiControl Agent",
                            "MobileIron Client",
                            "ObserveIT Client",
                            "OPSWAT Agent",
                            "Palo Alto Networks Cortex Agent",
                            "Qualys Agent",
                            "Quest Client",
                            "Redcloak Agent",
                            "Microsoft SCCM Client",
                            "Secdo Agent",
                            "SentinelOne Agent",
                            "Signalsciences Agent",
                            "Traps Agent",
                            "Eclypsium Agent",
                            "Malwarebytes Agent",
                            "Sophos Agent",
                            "Symantec SEP 14 Agent",
                            "Symantec Cloud Agent",
                            "Symantec Endpoint Encryption Agent",
                            "Symantec SEP 12 Agent",
                            "Tanium Agent",
                            "Tenable io Agent",
                            "Tripwire Agent",
                            "TrueFort Agent",
                            "Guardicore Agent",
                            "DeepSecurity Agent",
                            "Illusive Agent",
                            "Bitdefender Gravity Zone Agent",
                            "Avamar Client",
                            "Twistlock Agent",
                            "Webroot Agent",
                            "Aqua Enforcer",
                            "Symantec DLP Agent",
                            "Bitlocker Agent",
                            "Wazuh Agent",
                            "WSUS Client",
                            "Microfocus Server Automation",
                            "Contrast Security Agent"
                        ]
                    },
                    {
                        "title": "Version",
                        "type": "string",
                        "name": "agent_version",
                        "format": "version"
                    },
                    {
                        "title": "Status",
                        "type": "string",
                        "name": "agent_status"
                    }
                ]
            }
        },
        {
            "branched": true,
            "title": "Agent Versions: Name",
            "name": "agent_versions.adapter_name",
            "type": "string",
            "enum": [
                "Alert Logic Agent",
                "IBM BigFix Agent",
                "CarbonBlack Defense Sensor",
                "CarbonBlack Protection Sensor",
                "CarbonBlack Response Sensor",
                "Cisco AMP Connector",
                "Cisco FMC Agent",
                "Cisco Umbrella Agent",
                "CloudPassage Daemon",
                "Code42 Agent",
                "CounterACT Agent",
                "CrowdStrike Agent",
                "Cylance Agent",
                "Datadog Agent",
                "Desktop Central Agent",
                "Dropbox Client",
                "Druva Client",
                "Endgame Sensor",
                "enSilo Agent",
                "McAfee EPO Agent",
                "FireEye HX Agent",
                "Forcepoint Client",
                "Imperva DAM Agent",
                "JumpCloud Agent",
                "Kaseya Agent",
                "Lansweeper Agent",
                "Minerva Labs Agent",
                "MobiControl Agent",
                "MobileIron Client",
                "ObserveIT Client",
                "OPSWAT Agent",
                "Palo Alto Networks Cortex Agent",
                "Qualys Agent",
                "Quest Client",
                "Redcloak Agent",
                "Microsoft SCCM Client",
                "Secdo Agent",
                "SentinelOne Agent",
                "Signalsciences Agent",
                "Traps Agent",
                "Eclypsium Agent",
                "Malwarebytes Agent",
                "Sophos Agent",
                "Symantec SEP 14 Agent",
                "Symantec Cloud Agent",
                "Symantec Endpoint Encryption Agent",
                "Symantec SEP 12 Agent",
                "Tanium Agent",
                "Tenable io Agent",
                "Tripwire Agent",
                "TrueFort Agent",
                "Guardicore Agent",
                "DeepSecurity Agent",
                "Illusive Agent",
                "Bitdefender Gravity Zone Agent",
                "Avamar Client",
                "Twistlock Agent",
                "Webroot Agent",
                "Aqua Enforcer",
                "Symantec DLP Agent",
                "Bitlocker Agent",
                "Wazuh Agent",
                "WSUS Client",
                "Microfocus Server Automation",
                "Contrast Security Agent"
            ]
        },
        {
            "branched": true,
            "title": "Agent Versions: Version",
            "name": "agent_versions.agent_version",
            "type": "string",
            "format": "version"
        },
        {
            "branched": true,
            "title": "Agent Versions: Status",
            "name": "agent_versions.agent_status",
            "type": "string"
        },
        {
            "title": "Device Manufacturer",
            "type": "string",
            "name": "device_manufacturer"
        },
        {
            "title": "Adapter Properties",
            "type": "array",
            "name": "adapter_properties",
            "enum": [
                "Agent",
                "Endpoint_Protection_Platform",
                "Network",
                "Firewall",
                "Manager",
                "Vulnerability_Assessment",
                "Assets",
                "UserManagement",
                "Cloud_Provider",
                "Virtualization",
                "MDM"
            ],
            "items": {
                "type": "string",
                "enum": [
                    "Agent",
                    "Endpoint_Protection_Platform",
                    "Network",
                    "Firewall",
                    "Manager",
                    "Vulnerability_Assessment",
                    "Assets",
                    "UserManagement",
                    "Cloud_Provider",
                    "Virtualization",
                    "MDM"
                ]
            }
        },
        {
            "title": "Distinct Adapter Connections Count",
            "type": "number",
            "name": "adapter_count"
        }
    ],
    "fields": [
        "adapters",
        "adapter_list_length",
        "internal_axon_id",
        "hostname",
        "first_seen",
        "last_seen",
        "fetch_time",
        "first_fetch_time",
        "network_interfaces",
        "network_interfaces.name",
        "network_interfaces.mac",
        "network_interfaces.manufacturer",
        "network_interfaces.ips",
        "network_interfaces.subnets",
        "network_interfaces.vlan_list",
        "network_interfaces.vlan_list.name",
        "network_interfaces.vlan_list.tagid",
        "network_interfaces.vlan_list.tagness",
        "network_interfaces.operational_status",
        "network_interfaces.admin_status",
        "network_interfaces.speed",
        "network_interfaces.port_type",
        "network_interfaces.mtu",
        "network_interfaces.gateway",
        "network_interfaces.port",
        "os.type",
        "os.distribution",
        "os.is_windows_server",
        "os.os_str",
        "os.bitness",
        "os.sp",
        "os.install_date",
        "os.kernel_version",
        "os.codename",
        "os.major",
        "os.minor",
        "os.build",
        "os.serial",
        "connected_devices",
        "connected_devices.remote_name",
        "connected_devices.local_ifaces",
        "connected_devices.local_ifaces.name",
        "connected_devices.local_ifaces.mac",
        "connected_devices.local_ifaces.manufacturer",
        "connected_devices.local_ifaces.ips",
        "connected_devices.local_ifaces.subnets",
        "connected_devices.local_ifaces.vlan_list",
        "connected_devices.local_ifaces.vlan_list.name",
        "connected_devices.local_ifaces.vlan_list.tagid",
        "connected_devices.local_ifaces.vlan_list.tagness",
        "connected_devices.local_ifaces.operational_status",
        "connected_devices.local_ifaces.admin_status",
        "connected_devices.local_ifaces.speed",
        "connected_devices.local_ifaces.port_type",
        "connected_devices.local_ifaces.mtu",
        "connected_devices.local_ifaces.gateway",
        "connected_devices.local_ifaces.port",
        "connected_devices.remote_ifaces",
        "connected_devices.remote_ifaces.name",
        "connected_devices.remote_ifaces.mac",
        "connected_devices.remote_ifaces.manufacturer",
        "connected_devices.remote_ifaces.ips",
        "connected_devices.remote_ifaces.subnets",
        "connected_devices.remote_ifaces.vlan_list",
        "connected_devices.remote_ifaces.vlan_list.name",
        "connected_devices.remote_ifaces.vlan_list.tagid",
        "connected_devices.remote_ifaces.vlan_list.tagness",
        "connected_devices.remote_ifaces.operational_status",
        "connected_devices.remote_ifaces.admin_status",
        "connected_devices.remote_ifaces.speed",
        "connected_devices.remote_ifaces.port_type",
        "connected_devices.remote_ifaces.mtu",
        "connected_devices.remote_ifaces.gateway",
        "connected_devices.remote_ifaces.port",
        "connected_devices.connection_type",
        "id",
        "domain",
        "agent_versions",
        "agent_versions.adapter_name",
        "agent_versions.agent_version",
        "agent_versions.agent_status",
        "device_manufacturer",
        "adapter_properties",
        "labels",
        "hostname_preferred",
        "os.type_preferred",
        "os.distribution_preferred",
        "network_interfaces.mac_preferred",
        "network_interfaces.ips_preferred",
        "correlation_reasons"
    ]
}
    ''')
}
