from json_file_adapter.service import FILE_NAME, DEVICES_DATA, USERS_DATA
from test_helpers.file_mock_credentials import FileForCredentialsMock

client_details = [
    ({
        "host": "vcenter.axonius.lan",
        "user": "readonly@vsphere.local",
        "password": "a$Xvje99a$Xvje99",
        "verify_ssl": False,
        "rest_api": "https://vcenter.axonius.lan/api",
    }, '52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b')]
# This vcenter is currently not active!!! we should return it as soon as it becomes active again
# ({
#     "host": "vcenter51.axonius.lan",
#     "user": "root",
#     "password": "vmware",
#     "verify_ssl": False
# }, "525345eb-51ef-f4d7-85bb-08e521b94528"),
# ({
#     "host": "vcenter55.axonius.lan",
#     "user": "root",
#     "password": "vmware",
#     "verify_ssl": False
# }, "525d738d-c18f-ed57-6059-6d3378a61442")]

# vcenter vm
SOME_DEVICE_ID = '52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b'
# this is the ID of a VM that is inside a datacenter that is inside a folder
# it is called "just_for_datacenter_folders"
AGGREGATED_DEVICE_ID = "5011b327-7833-4d80-af9f-11c0afdde448"

# This is a template - make sure we don't get it
VERIFY_DEVICE_MISSING = "501129ea-6b2e-8ce5-c621-479d4aa454f6"


DEVICE_WITH_TAG = '5011020f-b710-e8b5-10a2-6c1ef0e0f791'
TAG_KEY = 'MARKtag'
TAG_VALUE = 'Marki mark is marks mark'

esx_json_file_mock_devices = {
    FILE_NAME: "ESX_MOCK",
    USERS_DATA: FileForCredentialsMock(USERS_DATA, ''),
    DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, """
    {
    "devices": [
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 500.0
                }
            ],
            "hostname": "axonius",
            "cloud_id": "50110718-eb5e-385f-3fc6-630489501ba6",
            "vm_path_name": "[sata-disk] export-test-1588288600.953932/export-test-1588288600.953932.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/export-test-1588288600.953932",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI CD/DVD drive 0"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-04-30 23:19:24",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:A1:36",
                    "ips_raw": [
                        3232240672,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.32",
                        "fe80::250:56ff:fe91:a136"
                    ]
                },
                {
                    "mac": "46:DD:32:7E:AC:24",
                    "ips_raw": [
                        null
                    ],
                    "ips": [
                        "fe80::44dd:32ff:fe7e:ac24"
                    ]
                },
                {
                    "mac": "B6:4B:06:AB:9D:19",
                    "ips_raw": [
                        null
                    ],
                    "ips": [
                        "fe80::b44b:6ff:feab:9d19"
                    ]
                },
                {
                    "mac": "EE:59:02:C1:25:63",
                    "ips_raw": [
                        null
                    ],
                    "ips": [
                        "fe80::ec59:2ff:fec1:2563"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 32.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 8,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit0",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 12,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42118867-97f1-a8be-1694-5041f72ca68e",
            "name": "export-test-1588288600.953932",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-1",
            "quick_id": "esx_adapter_0!50110718-eb5e-385f-3fc6-630489501ba6",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 500.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 20.0
                }
            ],
            "hostname": "ax-tailscalenode-esxi",
            "cloud_id": "5011a610-915b-bcfc-3e28-f2868cd2b8ce",
            "vm_path_name": "[sata-disk] AX-TailscaleNode/AX-TailscaleNode.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/AX-TailscaleNode",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/linux/ubuntu-18.04.3-live-server-amd64.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-04-30 14:35:18",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:0B:D1",
                    "ips_raw": [
                        3232240681
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.41"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit1",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 12,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "421122c2-8d6c-38c4-1cfe-1ce250cd8191",
            "name": "AX-TailscaleNode",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-2",
            "quick_id": "esx_adapter_0!5011a610-915b-bcfc-3e28-f2868cd2b8ce",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 20.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 100.0
                }
            ],
            "cloud_id": "50114d7d-ea5a-58d9-f14b-d304ced7ee26",
            "vm_path_name": "[sata-disk] New Virtual Machine/New Virtual Machine.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Hyper_V_2008R2_test%20(Itay)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage] nopassshare/GRMHVxFRE1_DVD.iso"
            ],
            "plugin_type": "Adapter",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:E7:EE",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 16.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotInstalled",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "Server 2008",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2008 r2 (64-bit)"
            },
            "id": "shit2",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "fetch_time": "2020-05-13 10:02:45",
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211f647-0823-9404-e32c-31efac66b390",
            "name": "Hyper_V_2008R2_test%20(Itay)",
            "pretty_id": "AX-3",
            "quick_id": "esx_adapter_0!50114d7d-ea5a-58d9-f14b-d304ced7ee26",
            "hds_total": 100.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "seci_ubuntu",
            "cloud_id": "50111369-f7f7-82a2-524e-de81614d5b8a",
            "vm_path_name": "[sata-disk] export_tester-2/export_tester-2.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/export_tester-2",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [sata-disk] export_tester-2/_deviceImage-1.iso",
                "ISO [sata-disk] export_tester-2/_deviceImage-2.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-05-13 14:58:36",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:75:31",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 2.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 1,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit3",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": -1,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42112ec0-d826-5651-0db5-43538e9207b0",
            "name": "export_tester-2",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-4",
            "quick_id": "esx_adapter_0!50111369-f7f7-82a2-524e-de81614d5b8a",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 40.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "localhost.axonius.lan",
            "cloud_id": "501127a3-fc86-24de-287d-896816c41c43",
            "vm_path_name": "[nl-sas-disk] ESX For Cluster 1/ESX For Cluster 1.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/ESX For Cluster 1",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/vmware/ESXi/6.5/VMware-VMvisor-Installer-6.5.0-4564106.x86_64.iso"
            ],
            "plugin_type": "Adapter",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:AE:DE",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "(?) vmware esxi 6.5 or later",
                "os_str": "vmware esxi 6.5 or later",
                "type": "VMWare"
            },
            "id": "shit4",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "fetch_time": "2020-05-13 10:02:45",
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42113e70-ffa5-1667-ec25-55079c9ce451",
            "name": "ESX For Cluster 1",
            "pretty_id": "AX-5",
            "quick_id": "esx_adapter_0!501127a3-fc86-24de-287d-896816c41c43",
            "hds_total": 40.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 24.0
                }
            ],
            "hostname": "testwindows7.TestDomain.test",
            "cloud_id": "5011eda9-ba3d-e6aa-e695-8d81b9170c2d",
            "vm_path_name": "[sata-disk] test_windows_7/test_windows_7.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/test_windows_7%20(Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage] nopassshare/installations/images/windows/en_windows_7_ultimate_with_sp1_x86_dvd_u_677460.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-09 23:57:32",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:AD:39",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 2.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "7",
                "is_windows_server": false,
                "bitness": 32,
                "type": "Windows",
                "os_str": "microsoft windows 7 (32-bit)"
            },
            "id": "shit5",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42112af7-b263-3065-6190-bae7893078ae",
            "name": "test_windows_7%20(Avidor)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-6",
            "quick_id": "esx_adapter_0!5011eda9-ba3d-e6aa-e695-8d81b9170c2d",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 24.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 100.0
                }
            ],
            "hostname": "resilient.localdomain",
            "cloud_id": "50112409-212d-9bf3-3d7b-260df3e0f3b0",
            "vm_path_name": "[sata-disk] IBM Resilient 30 (latest)/IBM Resilient 30 (latest).vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/IBM Resilient 30 (latest)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI"
            ],
            "plugin_type": "Adapter",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:31:17",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "Red Hat",
                "bitness": 64,
                "type": "Linux",
                "os_str": "red hat enterprise linux 7 (64-bit)"
            },
            "id": "shit6",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "fetch_time": "2020-05-13 10:02:45",
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211a8ef-a270-5a78-381e-39b703876242",
            "name": "IBM Resilient 30 (latest)",
            "pretty_id": "AX-7",
            "quick_id": "esx_adapter_0!50112409-212d-9bf3-3d7b-260df3e0f3b0",
            "hds_total": 100.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 100.0
                },
                {
                    "device": "Hard disk 2",
                    "total_size": 100.0
                },
                {
                    "device": "Hard disk 3",
                    "total_size": 100.0
                },
                {
                    "device": "Hard disk 4",
                    "total_size": 1.0
                },
                {
                    "device": "Hard disk 5",
                    "total_size": 200.0
                }
            ],
            "fetch_time": "2020-05-13 10:02:45",
            "cloud_id": "501184a3-6137-fa05-8691-a4ed1e44d28b",
            "vm_path_name": "[sata-disk] phantom-3.5.210.ova/phantom-3.5.210.ova.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/phantom-3.5.210.ova",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "Remote ATAPI"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:36:55",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:B9:74",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotInstalled",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "Red Hat",
                "bitness": 64,
                "type": "Linux",
                "os_str": "red hat enterprise linux 6 (64-bit)"
            },
            "id": "shit7",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42113644-70dd-836e-ea8f-39e15c6c1df1",
            "name": "phantom-3.5.210.ova",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-8",
            "quick_id": "esx_adapter_0!501184a3-6137-fa05-8691-a4ed1e44d28b",
            "hds_total": 501.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 60.0
                }
            ],
            "hostname": "nozomi-n2os.local",
            "cloud_id": "5011d149-be16-1992-9984-5dcdc3645f33",
            "vm_path_name": "[nl-sas-disk] nozomi/nozomi.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/nozomi",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "Remote device"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-03-26 13:56:16",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:5E:BF",
                    "ips_raw": [
                        3232240700
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.60"
                    ]
                },
                {
                    "mac": "00:50:56:91:51:0D",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "FreeBSD",
                "bitness": 64,
                "type": "FreeBSD",
                "os_str": "freebsd pre-11 versions (64-bit)"
            },
            "id": "shit8",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 47,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211ca37-36f6-f2ef-aa90-534d37737052",
            "name": "nozomi",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-9",
            "quick_id": "esx_adapter_0!5011d149-be16-1992-9984-5dcdc3645f33",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 60.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 64.0
                }
            ],
            "hostname": "ip-192-168-20-15.us-east-2.compute.internal",
            "cloud_id": "50112969-f6da-ceda-08dc-53f7d12cdabc",
            "vm_path_name": "[nl-sas-disk] rs_image_8.5.2-1995/rs_image_8.5.2-1995.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/RedStone_8.5.2-1995%20(Schwartz)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "Remote device"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:30:15",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:AC:93",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "bitness": 64,
                "type": "Linux",
                "os_str": "centos 4/5 or later (64-bit)"
            },
            "id": "shit9",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211a575-cec8-0cde-f019-80886f632cf6",
            "name": "RedStone_8.5.2-1995%20(Schwartz)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-10",
            "quick_id": "esx_adapter_0!50112969-f6da-ceda-08dc-53f7d12cdabc",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 64.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 200.0
                }
            ],
            "hostname": "ise-26",
            "cloud_id": "5011c2e2-3b18-d02b-bcdf-6fa47783a9ff",
            "vm_path_name": "[sata-disk] Hanan_ISE2.6/Hanan_ISE2.6.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Hanan_ISE2.6",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [sata-disk] ISE_ISO/ise-2.6.0.156.SPA.x86_64.iso"
            ],
            "plugin_type": "Adapter",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:66:C8",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 32.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "Red Hat",
                "bitness": 64,
                "type": "Linux",
                "os_str": "red hat enterprise linux 7 (64-bit)"
            },
            "id": "shit10",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "fetch_time": "2020-05-13 10:02:45",
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42118928-4dc3-c664-d4ff-036bff0890cb",
            "name": "Hanan_ISE2.6",
            "pretty_id": "AX-11",
            "quick_id": "esx_adapter_0!5011c2e2-3b18-d02b-bcdf-6fa47783a9ff",
            "hds_total": 200.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 128.0
                }
            ],
            "hostname": "gzva",
            "cloud_id": "50115908-974e-d64e-2aad-bc4d1c70d21c",
            "pretty_id": "AX-12",
            "vm_path_name": "[sata-disk] GravityZoneEnterprise/GravityZoneEnterprise.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/GravityZoneEnterprise",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "Remote device"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:37:29",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:F1:BB",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "tags": [
                {
                    "tag_key": "KK",
                    "tag_value": "YYY"
                }
            ],
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "cloud_provider": "VMWare",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit11",
            "vm_tools_status": "toolsNotRunning",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211b8ea-77eb-95a7-0645-81859fa17cc1",
            "name": "GravityZoneEnterprise",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "total_physical_memory": 8.0,
            "quick_id": "esx_adapter_0!50115908-974e-d64e-2aad-bc4d1c70d21c",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 128.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 25.0
                }
            ],
            "hostname": "op-iperf3",
            "cloud_id": "50113d7a-4e7f-6b29-b843-1e635e31b7db",
            "vm_path_name": "[sata-disk] Iperf3 - Gustavo/Iperf3 - Gustavo.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Iperf3 - Gustavo",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/linux/ubuntu-16.04.2-server-amd64.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-04-19 13:07:33",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:07:FC",
                    "ips_raw": [
                        3232240667
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.27"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit12",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 23,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211a52b-859a-987e-c1d5-2df827f5a6ad",
            "name": "Iperf3 - Gustavo",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-13",
            "quick_id": "esx_adapter_0!50113d7a-4e7f-6b29-b843-1e635e31b7db",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 25.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 50.0
                }
            ],
            "hostname": "DESKTOP-DEQSJLK",
            "cloud_id": "5011ab93-01e9-7fc4-af13-35a1334e367c",
            "vm_path_name": "[nl-sas-disk] TFTP Server/TFTP Server.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/TFTP Server",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/windows/en_windows_10_multiple_editions_version_1703_updated_march_2017_x64_dvd_10189288.iso"
            ],
            "plugin_type": "Adapter",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:F6:A8",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "10",
                "is_windows_server": false,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows 10 (64-bit)"
            },
            "id": "shit13",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "fetch_time": "2020-05-13 10:02:45",
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42119903-2da8-434f-68de-000530a1bb05",
            "name": "TFTP Server",
            "pretty_id": "AX-14",
            "quick_id": "esx_adapter_0!5011ab93-01e9-7fc4-af13-35a1334e367c",
            "hds_total": 50.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 30.0
                }
            ],
            "hostname": "op-devops-test",
            "cloud_id": "501145ef-3b90-c30d-ac41-00ab4da17178",
            "vm_path_name": "[sata-disk] Gustavo - Tests/Gustavo - Tests.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Gustavo - Tests",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/linux/ubuntu-18.04.3-live-server-amd64.iso"
            ],
            "plugin_type": "Adapter",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:6C:E6",
                    "ips_raw": [
                        3232240705,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.65",
                        "fe80::250:56ff:fe91:6ce6"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 16.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit14",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "fetch_time": "2020-05-13 10:02:45",
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42114e05-0acd-46fd-34a2-814f7076679f",
            "name": "Gustavo - Tests",
            "pretty_id": "AX-15",
            "quick_id": "esx_adapter_0!501145ef-3b90-c30d-ac41-00ab4da17178",
            "hds_total": 30.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "seci_ubuntu",
            "cloud_id": "5011f3c9-3d1b-ed3a-ed42-f93539bfd2a2",
            "vm_path_name": "[sata-disk] export_tester-3/export_tester-3.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/export_tester-3",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [sata-disk] export_tester-3/_deviceImage-1.iso",
                "ISO [sata-disk] export_tester-3/_deviceImage-2.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-05-13 15:15:19",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:DA:3D",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 2.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 1,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit15",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": -1,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42119731-1d2c-04ac-9b79-a9a34993ee16",
            "name": "export_tester-3",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-16",
            "quick_id": "esx_adapter_0!5011f3c9-3d1b-ed3a-ed42-f93539bfd2a2",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 40.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 64.0
                }
            ],
            "hostname": "eset.axonius.lan",
            "cloud_id": "5011555a-1bf8-63b6-4878-5ee492c2bf17",
            "vm_path_name": "[sata-disk] eset_remote_endpoint_admin/eset_remote_endpoint_admin.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/eset_remote_endpoint_admin_server_appliance%20(Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "Remote ATAPI"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:03:40",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:A6:6B",
                    "ips_raw": [
                        3232240692,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.52",
                        "fe80::250:56ff:fe91:a66b"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "bitness": 64,
                "type": "Linux",
                "os_str": "centos 4/5 or later (64-bit)"
            },
            "id": "shit16",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211bf16-0b1f-02de-946d-619262116959",
            "name": "eset_remote_endpoint_admin_server_appliance%20(Avidor)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-17",
            "quick_id": "esx_adapter_0!5011555a-1bf8-63b6-4878-5ee492c2bf17",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 64.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 64.0
                }
            ],
            "hostname": "TOC-fb0de686",
            "cloud_id": "5011afa3-b6e8-b987-4933-8351645cd49a",
            "vm_path_name": "[sata-disk] TOC-1.3.1.ova/TOC-1.3.1.ova.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/TOC-1.3.1.ova",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:30:56",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:9B:5A",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 7.90625,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "Red Hat",
                "bitness": 64,
                "type": "Linux",
                "os_str": "red hat enterprise linux 6 (64-bit)"
            },
            "id": "shit17",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "421126bb-237d-8f74-c0e9-1d2f0a8caf7a",
            "name": "TOC-1.3.1.ova",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-18",
            "quick_id": "esx_adapter_0!5011afa3-b6e8-b987-4933-8351645cd49a",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 64.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "seci_ubuntu",
            "cloud_id": "501185be-21c8-891b-e253-4f3462c54cf3",
            "vm_path_name": "[sata-disk] ubuntu_bionic_se_ci_base-45/ubuntu_bionic_se_ci_base-45.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/ubuntu_bionic_se_ci_base-45",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [sata-disk] ubuntu_bionic_se_ci_base-45/_deviceImage-1.iso",
                "ISO [sata-disk] ubuntu_bionic_se_ci_base-45/_deviceImage-2.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-02-23 01:00:19",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:54:9B",
                    "ips_raw": [
                        3232240688,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.48",
                        "fe80::250:56ff:fe91:549b"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 2.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 1,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit18",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 80,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211eccc-ce16-151d-9439-8a66ff1d4c28",
            "name": "ubuntu_bionic_se_ci_base-45",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-19",
            "quick_id": "esx_adapter_0!501185be-21c8-891b-e253-4f3462c54cf3",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 40.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "seci_ubuntu",
            "cloud_id": "50118316-702c-28e1-f878-b46014a4268e",
            "vm_path_name": "[sata-disk] ubuntu_bionic_se_ci_base-44/ubuntu_bionic_se_ci_base-44.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/ubuntu_bionic_se_ci_base-44",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [sata-disk] ubuntu_bionic_se_ci_base-44/_deviceImage-1.iso",
                "ISO [sata-disk] ubuntu_bionic_se_ci_base-44/_deviceImage-2.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-02-23 01:00:20",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:C8:ED",
                    "ips_raw": [
                        3232240688,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.48",
                        "fe80::250:56ff:fe91:c8ed"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 2.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 1,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit19",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 80,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211a6ce-0054-c12b-e29f-42ae825c611e",
            "name": "ubuntu_bionic_se_ci_base-44",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-20",
            "quick_id": "esx_adapter_0!50118316-702c-28e1-f878-b46014a4268e",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 40.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "seci_ubuntu",
            "cloud_id": "5011d1e7-6afe-2b1e-c8db-cf879ea6e8e2",
            "vm_path_name": "[sata-disk] ubuntu_bionic_se_ci_base/ubuntu_bionic_se_ci_base.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/ubuntu_bionic_se_ci_base",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [sata-disk] ubuntu_bionic_se_ci_base/_deviceImage-1.iso",
                "ISO [sata-disk] ubuntu_bionic_se_ci_base/_deviceImage-2.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-02-24 15:30:55",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:9C:ED",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit20",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 78,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211a471-8207-ff52-95d5-e811cb6a2ce5",
            "name": "ubuntu_bionic_se_ci_base",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-21",
            "quick_id": "esx_adapter_0!5011d1e7-6afe-2b1e-c8db-cf879ea6e8e2",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 40.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 64.0
                }
            ],
            "hostname": "ip-192-168-20-63.us-east-2.compute.internal",
            "cloud_id": "50118a12-526d-f5e2-9b51-8905bb0c31c5",
            "vm_path_name": "[nl-sas-disk] rs-va-9_3_3-2901_1/rs-va-9_3_3-2901.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/rs-va-9_3_3-2901",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "Remote device"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-05-03 23:31:22",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:4F:C9",
                    "ips_raw": [
                        3232240703,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.63",
                        "fe80::250:56ff:fe91:4fc9"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "bitness": 64,
                "type": "Linux",
                "os_str": "centos 4/5 or later (64-bit)"
            },
            "id": "shit21",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 9,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "421190e8-b535-bb19-3d78-24b613a70b20",
            "name": "rs-va-9_3_3-2901",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-22",
            "quick_id": "esx_adapter_0!50118a12-526d-f5e2-9b51-8905bb0c31c5",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 64.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 2",
                    "total_size": 1.8447265625
                },
                {
                    "device": "Hard disk 1",
                    "total_size": 12.0
                },
                {
                    "device": "Hard disk 11",
                    "total_size": 10.0
                },
                {
                    "device": "Hard disk 12",
                    "total_size": 100.0
                },
                {
                    "device": "Hard disk 13",
                    "total_size": 50.0
                },
                {
                    "device": "Hard disk 6",
                    "total_size": 10.0
                },
                {
                    "device": "Hard disk 8",
                    "total_size": 10.0
                },
                {
                    "device": "Hard disk 9",
                    "total_size": 1.0
                },
                {
                    "device": "Hard disk 3",
                    "total_size": 25.0
                },
                {
                    "device": "Hard disk 10",
                    "total_size": 10.0
                },
                {
                    "device": "Hard disk 4",
                    "total_size": 25.0
                },
                {
                    "device": "Hard disk 5",
                    "total_size": 10.0
                },
                {
                    "device": "Hard disk 7",
                    "total_size": 15.0
                }
            ],
            "hostname": "vcenter.axonius.local",
            "cloud_id": "5011e2ec-bd9e-5da8-70cb-1791a6c5c134",
            "vm_path_name": "[sata-disk] vCenter6.7/vCenter6.7.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/vCenter6.7",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI CD/DVD drive 0"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-12 11:53:49",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:D6:DE",
                    "ips_raw": [
                        3232240645
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.5"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 10.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "bitness": 64,
                "type": "Linux",
                "os_str": "other 3.x linux (64-bit)"
            },
            "id": "shit22",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 121,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211c8d5-983b-c501-0f2f-db6363f00351",
            "name": "vCenter6.7",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-23",
            "quick_id": "esx_adapter_0!5011e2ec-bd9e-5da8-70cb-1791a6c5c134",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 279.8447265625,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 250.0
                }
            ],
            "hostname": "management",
            "cloud_id": "501110a1-6fb1-9e1e-3b5e-613cbb139e29",
            "vm_path_name": "[sata-disk] preempt_platform_management_3.1.1847/preempt_platform_management_3.1.1847.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/preempt_platform_management_3.1.1847",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "Remote device"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-03-22 22:22:06",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:7C:92",
                    "ips_raw": [
                        3232240691,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.51",
                        "fe80::250:56ff:fe91:7c92"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 6,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit23",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 51,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "421162d9-3cf0-fa6c-006e-57460d9547fd",
            "name": "preempt_platform_management_3.1.1847",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-24",
            "quick_id": "esx_adapter_0!501110a1-6fb1-9e1e-3b5e-613cbb139e29",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 250.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "localhost.axonius.lan",
            "cloud_id": "50113be6-59db-3d70-db49-0655d1e7c32e",
            "vm_path_name": "[nl-sas-disk] ESX For Cluster 2/ESX For Cluster 2.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/ESX For Cluster 2",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/vmware/ESXi/6.5/VMware-VMvisor-Installer-6.5.0-4564106.x86_64.iso"
            ],
            "plugin_type": "Adapter",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "network_interfaces": [
                {
                    "mac": "00:50:56:24:A1:CE",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "(?) vmware esxi 6.5 or later",
                "os_str": "vmware esxi 6.5 or later",
                "type": "VMWare"
            },
            "id": "shit24",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "fetch_time": "2020-05-13 10:02:45",
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211915c-af9e-32f9-b2d0-ed6f94a983fc",
            "name": "ESX For Cluster 2",
            "pretty_id": "AX-25",
            "quick_id": "esx_adapter_0!50113be6-59db-3d70-db49-0655d1e7c32e",
            "hds_total": 40.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 400.0
                }
            ],
            "fetch_time": "2020-05-13 10:02:45",
            "cloud_id": "501152ce-72a9-f1bd-dd7d-c0b13973011b",
            "vm_path_name": "[sata-disk] Hyper_V_2016_test/Hyper_V_2016_test.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Hyper_V_2016_test%20(Itay)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage] nopassshare/installations/images/windows/en_windows_server_2016_x64_dvd_9718492.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-04-27 21:00:08",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:5B:A0",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 32.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsNotInstalled",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 12,
            "os": {
                "distribution": "Server 2016",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2016 (64-bit)"
            },
            "id": "shit25",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 15,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211face-ea91-c68a-eb8b-d1e7fe234c76",
            "name": "Hyper_V_2016_test%20(Itay)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-26",
            "quick_id": "esx_adapter_0!501152ce-72a9-f1bd-dd7d-c0b13973011b",
            "hds_total": 400.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 2",
                    "total_size": 1.7529296875
                },
                {
                    "device": "Hard disk 11",
                    "total_size": 10.0
                },
                {
                    "device": "Hard disk 7",
                    "total_size": 15.0
                },
                {
                    "device": "Hard disk 12",
                    "total_size": 100.0
                },
                {
                    "device": "Hard disk 6",
                    "total_size": 10.0
                },
                {
                    "device": "Hard disk 8",
                    "total_size": 10.0
                },
                {
                    "device": "Hard disk 9",
                    "total_size": 1.0
                },
                {
                    "device": "Hard disk 3",
                    "total_size": 25.0
                },
                {
                    "device": "Hard disk 10",
                    "total_size": 10.0
                },
                {
                    "device": "Hard disk 1",
                    "total_size": 12.0
                },
                {
                    "device": "Hard disk 4",
                    "total_size": 25.0
                },
                {
                    "device": "Hard disk 5",
                    "total_size": 10.0
                }
            ],
            "hostname": "localhost.localdom",
            "cloud_id": "52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b",
            "vm_path_name": "[sata-disk] vCenter/vCenter.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Production/vCenter 6.5 (Old)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI CD/DVD drive 0"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-09 23:47:22",
            "network_interfaces": [
                {
                    "mac": "00:0C:29:0A:BA:12",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 10.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "bitness": 64,
                "type": "Linux",
                "os_str": "other 3.x linux (64-bit)"
            },
            "id": "shit26",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564da946-f109-bd1d-a1ad-872aec0aba12",
            "name": "vCenter 6.5 (Old)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-27",
            "quick_id": "esx_adapter_0!52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 229.7529296875
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 60.0
                }
            ],
            "hostname": "dc1.axonius.local",
            "cloud_id": "526c3f0c-41e7-4807-071d-8820dd6dba3f",
            "vm_path_name": "[nl-sas-disk] Network Controller/Network Controller.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Production/domaincontrol%20and%20dns%20(Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage] installations/images/windows/en_windows_server_2016_x64_dvd_9718492.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-03-22 23:12:07",
            "network_interfaces": [
                {
                    "mac": "00:0C:29:F1:0D:5B",
                    "ips_raw": [
                        3232240644
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.4"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "Server 2016",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2016 (64-bit)"
            },
            "id": "shit27",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 51,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564d16d5-5b10-6ab4-3789-2af7baf10d5b",
            "name": "domaincontrol%20and%20dns%20(Avidor)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-28",
            "quick_id": "esx_adapter_0!526c3f0c-41e7-4807-071d-8820dd6dba3f",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 60.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 8.0
                },
                {
                    "device": "Hard disk 2",
                    "total_size": 1024.0
                }
            ],
            "hostname": "storage.axonius.lan",
            "cloud_id": "521690a4-7434-7dd4-ff4e-9ff4a4274246",
            "vm_path_name": "[sata-disk] storage-server/storage-server.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Production/storageserver-avidor",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI /vmfs/devices/cdrom/mpx.vmhba1:C0:T5:L0"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-09 23:47:12",
            "network_interfaces": [
                {
                    "mac": "00:0C:29:B5:94:F8",
                    "ips_raw": [
                        3232240643
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.3"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "FreeBSD",
                "bitness": 64,
                "type": "FreeBSD",
                "os_str": "freebsd pre-11 versions (64-bit)"
            },
            "id": "shit28",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564d3a19-50f6-9569-ce0c-af0ba5b594f8",
            "name": "storageserver-avidor",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-29",
            "quick_id": "esx_adapter_0!521690a4-7434-7dd4-ff4e-9ff4a4274246",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 1032.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 30.0
                }
            ],
            "cloud_id": "522e70a8-d6a8-1b89-781b-710338224f0a",
            "vm_path_name": "[nl-sas-disk] Carbon_Black_OS_6.2.0.171114.1158/Carbon_Black_OS_6.2.0.171114.1158.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Discovered virtual machine/Carbon_Black_OS_6.2.0.171114.1158%20(Ofri)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI /vmfs/devices/cdrom/mpx.vmhba1:C0:T5:L0",
                "ISO [storage_nopass] installations/Carbon Black/cbos_6.2.0.171114.1158.iso"
            ],
            "plugin_type": "Adapter",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "network_interfaces": [
                {
                    "mac": "00:0C:29:16:F6:68",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 3.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotInstalled",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "bitness": 64,
                "os_str": "other (64-bit)"
            },
            "id": "shit29",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "fetch_time": "2020-05-13 10:02:45",
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564d41ef-70ce-bd84-00ed-57de6216f668",
            "name": "Carbon_Black_OS_6.2.0.171114.1158%20(Ofri)",
            "pretty_id": "AX-30",
            "quick_id": "esx_adapter_0!522e70a8-d6a8-1b89-781b-710338224f0a",
            "hds_total": 30.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 120.0
                }
            ],
            "hostname": "dc4.TestDomain.test",
            "cloud_id": "52d4a115-c556-b8f3-015a-e41634c4d250",
            "vm_path_name": "[nl-sas-disk] Windows Server 2012 r2 westdc2.west.TestDomain.test/Windows Server 2012 r2 westdc2.west.TestDomain.test.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Discovered virtual machine/Windows%20Server%202012%20r2%20dc4.TestDomain.test%20(Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/windows/lync/en_lync_server_2013_x64_dvd_1043673.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-04-20 10:31:45",
            "network_interfaces": [
                {
                    "mac": "00:0C:29:B6:DA:46",
                    "ips_raw": [
                        null,
                        3232240657
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "fe80::5138:e88:7e48:9e5c",
                        "192.168.20.17"
                    ]
                },
                {
                    "mac": "00:0C:29:B6:DA:46",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 12.125,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "Server 2012",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2012 (64-bit)"
            },
            "id": "shit30",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 22,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564df7ab-c0b0-6b09-a643-45eadcb6da46",
            "name": "Windows%20Server%202012%20r2%20dc4.TestDomain.test%20(Avidor)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-31",
            "quick_id": "esx_adapter_0!52d4a115-c556-b8f3-015a-e41634c4d250",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 120.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "westdc1.west.TestDomain.test",
            "cloud_id": "52b77e4f-5aa7-940c-f541-3395a8f20c9e",
            "vm_path_name": "[nl-sas-disk] Windows Server 2012 r2 sub.TestDomain.test/Windows Server 2012 r2 sub.TestDomain.test.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Discovered virtual machine/Windows%20Server%202012%20r2%20westdc1.west.TestDomain.test%20(Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/windows/exchange/mu_exchange_server_2013_x64_dvd_1112105.iso"
            ],
            "plugin_type": "Adapter",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "network_interfaces": [
                {
                    "mac": "00:0C:29:64:CB:27",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "Server 2008",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2008 r2 (64-bit)"
            },
            "id": "shit31",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "fetch_time": "2020-05-13 10:02:45",
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564d4f74-14f9-e244-ae8d-a9421564cb27",
            "name": "Windows%20Server%202012%20r2%20westdc1.west.TestDomain.test%20(Avidor)",
            "pretty_id": "AX-32",
            "quick_id": "esx_adapter_0!52b77e4f-5aa7-940c-f541-3395a8f20c9e",
            "hds_total": 40.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 32.0
                }
            ],
            "hostname": "windows8.TestDomain.test",
            "cloud_id": "52266d8c-c049-5124-8124-9ee248a022f9",
            "vm_path_name": "[sata-disk] test_windows_8/test_windows_8.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Discovered virtual machine/test_windows_8_server_1%20(Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "fetch_time": "2020-05-13 10:02:45",
            "plugin_type": "Adapter",
            "boot_time": "2020-03-24 16:47:18",
            "network_interfaces": [
                {
                    "mac": "00:0C:29:80:0E:60",
                    "ips_raw": [
                        null,
                        3232240649
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "fe80::7900:ce14:d98e:a58",
                        "192.168.20.9"
                    ]
                },
                {
                    "mac": "00:0C:29:80:0E:60",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "8",
                "is_windows_server": false,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows 8.x (64-bit)"
            },
            "id": "shit32",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 49,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564d181b-d21a-c8f9-43e2-73bc2a800e60",
            "name": "test_windows_8_server_1%20(Avidor)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-33",
            "quick_id": "esx_adapter_0!52266d8c-c049-5124-8124-9ee248a022f9",
            "hds_total": 32.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "ip-192-168-20-22.us-east-2.compute.internal",
            "cloud_id": "522c9e34-a53f-5464-765b-ac20054edfb3",
            "vm_path_name": "[nl-sas-disk] Qualys Virtual appliance scanner/Qualys Virtual appliance scanner.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Discovered virtual machine/Qualys%20Virtual%20appliance%20scanner%20(Ofri)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI CD/DVD drive 0"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:01:30",
            "network_interfaces": [
                {
                    "mac": "00:0C:29:4B:5E:64",
                    "ips_raw": [
                        3232240662
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.22"
                    ]
                },
                {
                    "mac": "00:0C:29:4B:5E:64",
                    "manufacturer": "VMware (VMware, Inc.)"
                },
                {
                    "mac": "00:0C:29:4B:5E:6E",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 2.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 1,
            "os": {
                "distribution": "Red Hat",
                "bitness": 32,
                "type": "Linux",
                "os_str": "red hat enterprise linux 5 (32-bit)"
            },
            "id": "shit33",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564d38d6-c2aa-fc52-3730-c6a0e04b5e64",
            "name": "Qualys%20Virtual%20appliance%20scanner%20(Ofri)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-34",
            "quick_id": "esx_adapter_0!522c9e34-a53f-5464-765b-ac20054edfb3",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 40.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 32.0
                }
            ],
            "hostname": "DESKTOP-MPP10U1.TestDomain.test",
            "cloud_id": "52d2e602-cb77-5270-3998-21c5e64bd071",
            "vm_path_name": "[sata-disk] test_windows_1/test_windows_1.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Discovered virtual machine/test_windows_10_server_1%20(Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "fetch_time": "2020-05-13 10:02:45",
            "plugin_type": "Adapter",
            "boot_time": "2020-01-09 23:52:36",
            "network_interfaces": [
                {
                    "mac": "00:0C:29:45:B8:19",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "10",
                "is_windows_server": false,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows 10 (64-bit)"
            },
            "id": "shit34",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564dce9a-f36c-9708-736c-b6983d45b819",
            "name": "test_windows_10_server_1%20(Avidor)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-35",
            "quick_id": "esx_adapter_0!52d2e602-cb77-5270-3998-21c5e64bd071",
            "hds_total": 32.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "dc2.TestDomain.test",
            "cloud_id": "52e5f30a-82cb-21f5-30cc-1bf373d0f509",
            "vm_path_name": "[nl-sas-disk] Windows Server 2016 dc2.TestDomain.test/Windows Server 2016 dc2.TestDomain.test.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Discovered virtual machine/Windows%20Server%202016%20dc2.TestDomain.test%20(Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/windows/en_windows_server_2016_x64_dvd_9718492.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-04-20 10:33:18",
            "network_interfaces": [
                {
                    "mac": "00:0C:29:81:6C:4A",
                    "ips_raw": [
                        3232240677
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.37"
                    ]
                },
                {
                    "mac": "00:0C:29:81:6C:4A",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 12.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "Server 2016",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2016 (64-bit)"
            },
            "id": "shit35",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 22,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564dd294-8ec8-eb78-da93-e414c4816c4a",
            "name": "Windows%20Server%202016%20dc2.TestDomain.test%20(Avidor)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-36",
            "quick_id": "esx_adapter_0!52e5f30a-82cb-21f5-30cc-1bf373d0f509",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 40.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "dc1.TestDomain.test",
            "cloud_id": "52a5177d-3ba9-7e1d-7d1b-917e075cba57",
            "vm_path_name": "[nl-sas-disk] Windows Server 2016 Testdomain.Test/Windows Server 2016 Testdomain.Test.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Discovered virtual machine/Windows Server 2016 dc1.Testdomain.test (Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/windows/en_windows_server_2016_x64_dvd_9718492.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-04-20 10:34:47",
            "network_interfaces": [
                {
                    "mac": "00:0C:29:C6:95:5A",
                    "ips_raw": [
                        3232240665
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.25"
                    ]
                },
                {
                    "mac": "00:0C:29:C6:95:5A",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 16.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 6,
            "os": {
                "distribution": "Server 2016",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2016 (64-bit)"
            },
            "id": "shit36",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 22,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564d1b18-1f03-86b3-03f4-ab70a7c6955a",
            "name": "Windows Server 2016 dc1.Testdomain.test (Avidor)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-37",
            "quick_id": "esx_adapter_0!52a5177d-3ba9-7e1d-7d1b-917e075cba57",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 40.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 32.0
                }
            ],
            "hostname": "DESKTOP-GO8PIUL.TestSecDomain.test",
            "cloud_id": "526646f7-10b7-43e1-7958-7d06a4159862",
            "vm_path_name": "[sata-disk] test_windows_10_server_2/test_windows_10_server_2.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Discovered virtual machine/test_windows_10_server_2%20(Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage] installations/images/windows/en_windows_10_multiple_editions_version_1703_updated_march_2017_x64_dvd_10189288.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-09 23:54:28",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:CD:30",
                    "ips_raw": [
                        null,
                        3232240660
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "fe80::d175:4879:f855:230b",
                        "192.168.20.20"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 1,
            "os": {
                "distribution": "10",
                "is_windows_server": false,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows 10 (64-bit)"
            },
            "id": "shit37",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564db954-6c10-2472-f033-f5069430b7b6",
            "name": "test_windows_10_server_2%20(Avidor)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-38",
            "quick_id": "esx_adapter_0!526646f7-10b7-43e1-7958-7d06a4159862",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 32.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "hostname": "raindc1.raindomain.test",
            "cloud_id": "52ed62ec-a821-38b9-4c99-08ce72558ebf",
            "vm_path_name": "[nl-sas-disk] Windows Server 2016 dc1.RainForest.test/Windows Server 2016 dc1.RainForest.test.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Discovered virtual machine/Windows-Server-2016-raindc1.RainDomain.test(Avidor)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage_nopass] installations/images/windows/en_windows_server_2016_x64_dvd_9718492.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-04-14 18:45:40",
            "network_interfaces": [
                {
                    "mac": "00:0C:29:61:DD:22",
                    "ips_raw": [
                        null,
                        3232240678
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "fe80::fd5d:14a:e985:76e",
                        "192.168.20.38"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 16.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "Server 2016",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2016 (64-bit)"
            },
            "id": "shit38",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 28,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "564deb3f-cedf-4382-a3b3-48133961dd22",
            "name": "Windows-Server-2016-raindc1.RainDomain.test(Avidor)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-39",
            "quick_id": "esx_adapter_0!52ed62ec-a821-38b9-4c99-08ce72558ebf",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 40.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 244.140625
                }
            ],
            "hostname": "infoblox.axonius.lan",
            "cloud_id": "50112b5a-d625-bfc5-6549-b15d2a00c163",
            "vm_path_name": "[nl-sas-disk] InfoBlox-DDI_Trial_nios-8.2.4-366880-2018-02-09-06-18-49-ddi/InfoBlox-DDI_Trial_nios-8.2.4-366880-2018-02-09-06-18-49-ddi.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Tests/InfoBlox-DDI_Trial_nios-8.2.4-366880-2018-02-09-06-18-49-ddi",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:32:55",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:83:40",
                    "manufacturer": "VMware (VMware, Inc.)"
                },
                {
                    "mac": "00:50:56:91:1F:E0",
                    "manufacturer": "VMware (VMware, Inc.)"
                },
                {
                    "mac": "00:50:56:91:24:A3",
                    "manufacturer": "VMware (VMware, Inc.)"
                },
                {
                    "mac": "00:50:56:91:80:46",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 16.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "bitness": 64,
                "os_str": "other (64-bit)"
            },
            "id": "shit39",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "421129a2-d788-8935-efb0-7188903ddaf2",
            "name": "InfoBlox-DDI_Trial_nios-8.2.4-366880-2018-02-09-06-18-49-ddi",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-40",
            "quick_id": "esx_adapter_0!50112b5a-d625-bfc5-6549-b15d2a00c163",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 244.140625
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 60.0
                }
            ],
            "hostname": "NetMRI-VM",
            "cloud_id": "5011be62-b0d1-4422-bcc6-69e246d82b71",
            "vm_path_name": "[sata-disk] NetMRI-7.3.3/NetMRI-7.3.3.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Tests/Alex/NetMRI-7.3.3",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "fetch_time": "2020-05-13 10:02:45",
            "plugin_type": "Adapter",
            "boot_time": "2020-04-27 19:49:31",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:76:E3",
                    "ips_raw": [
                        3232240670,
                        2851995905,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.30",
                        "169.254.1.1",
                        "fe80::250:56ff:fe91:76e3"
                    ]
                },
                {
                    "mac": "00:50:56:91:76:E3",
                    "ips_raw": [
                        3232240671,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.31",
                        "fe80::250:56ff:fe91:76e3"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "bitness": 64,
                "type": "Linux",
                "os_str": "other 2.6.x linux (64-bit)"
            },
            "id": "shit40",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 15,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211a8a8-13a2-4aac-e8f8-e0ae381204a3",
            "name": "NetMRI-7.3.3",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-41",
            "quick_id": "esx_adapter_0!5011be62-b0d1-4422-bcc6-69e246d82b71",
            "hds_total": 60.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "cloud_id": "5011ed89-fd6d-5177-8632-ed0ab0d187a9",
            "vm_path_name": "[sata-disk] EmptyVM2/EmptyVM2.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Tests/Graf/EmptyVM2",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "plugin_type": "Adapter",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:3C:21",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotInstalled",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 1,
            "os": {
                "distribution": "Server 2016",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2016 (64-bit)"
            },
            "id": "shit41",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "fetch_time": "2020-05-13 10:02:45",
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211389c-1a48-0f6e-50ba-0bb19aaef23d",
            "name": "EmptyVM2",
            "pretty_id": "AX-42",
            "quick_id": "esx_adapter_0!5011ed89-fd6d-5177-8632-ed0ab0d187a9",
            "hds_total": 40.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "fetch_time": "2020-05-13 10:02:45",
            "cloud_id": "50119a20-1b92-0d93-81ee-d4cefc9379fc",
            "vm_path_name": "[sata-disk] EmptyVM/EmptyVM.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Tests/Graf/test/EmptyVM",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "plugin_type": "Adapter",
            "boot_time": "2020-03-31 19:00:53",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:F0:9D",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotInstalled",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 1,
            "os": {
                "distribution": "Server 2016",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2016 (64-bit)"
            },
            "id": "shit42",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 42,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42110a87-d085-474c-021f-68f2bf99f8aa",
            "name": "EmptyVM",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-43",
            "quick_id": "esx_adapter_0!50119a20-1b92-0d93-81ee-d4cefc9379fc",
            "hds_total": 40.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 16.0
                }
            ],
            "hostname": "cisco-emulator",
            "cloud_id": "501132f4-8a2b-e255-9fc3-0ad7c19ca63f",
            "vm_path_name": "[nl-sas-disk] cisco emulator/cisco emulator.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Tests/Schwartz/cisco-emulator-schwartz",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [storage-nopass] installations/images/linux/ubuntu-16.04.2-server-amd64.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:09:48",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:4F:24",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 1,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit43",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42112c3d-a2c2-9b72-f26b-77ace3af60db",
            "name": "cisco-emulator-schwartz",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-44",
            "quick_id": "esx_adapter_0!501132f4-8a2b-e255-9fc3-0ad7c19ca63f",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 16.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 300.0
                }
            ],
            "hostname": "prime",
            "cloud_id": "5011407c-977e-b55c-0f25-a89f26ef18b7",
            "vm_path_name": "[nl-sas-disk] PI-VA-3.2.0.0.258_SIGNED/PI-VA-3.2.0.0.258_SIGNED.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Tests/Schwartz/Cisco%20Prime%20(Schwartz)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:09:12",
            "network_interfaces": [
                {
                    "mac": "00:50:56:23:C1:9A",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 12.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 4,
            "os": {
                "distribution": "Red Hat",
                "bitness": 64,
                "type": "Linux",
                "os_str": "red hat enterprise linux 5 (64-bit)"
            },
            "id": "shit44",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211a19c-1ed9-2536-82ad-de740666e2fd",
            "name": "Cisco%20Prime%20(Schwartz)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-45",
            "quick_id": "esx_adapter_0!5011407c-977e-b55c-0f25-a89f26ef18b7",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 300.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 100.0
                }
            ],
            "hostname": "demistoserver",
            "cloud_id": "5011d581-ecea-4bba-3456-0ea52003af19",
            "vm_path_name": "[nl-sas-disk] demisto/demisto.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Tests/Schwartz/demisto",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "Remote device"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:38:55",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:AB:B4",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOff",
            "vm_tools_status": "toolsNotRunning",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "bitness": 64,
                "type": "Linux",
                "os_str": "centos 4/5 or later (64-bit)"
            },
            "id": "shit45",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42115b9a-f84e-c8a6-60c7-fdba384360a7",
            "name": "demisto",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-46",
            "quick_id": "esx_adapter_0!5011d581-ecea-4bba-3456-0ea52003af19",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 100.0
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 97.65625
                }
            ],
            "hostname": "nexpose",
            "cloud_id": "50117c85-e94d-544f-9bf0-40bf6f73e5ea",
            "vm_path_name": "[sata-disk] Rapid7VA_2/Rapid7VA.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/Tests/Itay/Rapid7VA%20(Itay)",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-01-10 00:03:34",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:00:66",
                    "ips_raw": [
                        3232240650,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.10",
                        "fe80::250:56ff:fe91:66"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 2,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit46",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 124,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211cc00-09db-ea6d-d57d-5d20f70df102",
            "name": "Rapid7VA%20(Itay)",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-47",
            "quick_id": "esx_adapter_0!50117c85-e94d-544f-9bf0-40bf6f73e5ea",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 97.65625,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hostname": "esx.axonius.local",
            "cloud_id": "4c4c4544-0033-3710-8032-b6c04f4e4b32",
            "pretty_id": "AX-48",
            "plugin_unique_name": "esx_adapter_0",
            "vm_physical_path": "/Root/Datacenter/cluster-test",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "boot_time": "2020-01-09 23:40:35",
            "plugin_type": "Adapter",
            "plugin_name": "esx_adapter",
            "tags": [
                {
                    "tag_key": "KK",
                    "tag_value": "YYY"
                }
            ],
            "total_physical_memory": 255.9065284729004,
            "power_state": "TurnedOn",
            "cloud_provider": "VMWare",
            "type": "entitydata",
            "os": {
                "distribution": "(?) vmware esxi 6.5.0 build-5969303",
                "os_str": "vmware esxi 6.5.0 build-5969303",
                "type": "VMWare"
            },
            "id": "shit47",
            "connection_hostname": "vcenter.axonius.lan",
            "cpus": [
                {
                    "ghz": 2.0478515625,
                    "cores": 32
                }
            ],
            "uptime": 124,
            "device_type": "ESXHost",
            "last_seen": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4c4c4544-0033-3710-8032-b6c04f4e4b32",
            "fetch_time": "2020-05-13 10:02:45",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "system_identifying_info": [],
            "quick_id": "esx_adapter_0!4c4c4544-0033-3710-8032-b6c04f4e4b32",
            "device_manufacturer": "Dell Inc.",
            "device_model": "PowerEdge T430",
            "name": "cluster-test",
            "bios_version": "2.4.2",
            "network_interfaces": [
                {
                    "mac": "18:66:DA:AF:37:40",
                    "ips_raw": [
                        3232240642
                    ],
                    "manufacturer": "Dell (Dell Inc.)",
                    "ips": [
                        "192.168.20.2"
                    ]
                }
            ]
        },
        {
            "hostname": "192.168.20.31",
            "cloud_id": "703e1142-a5ff-6716-ec25-55079c9ce451",
            "plugin_unique_name": "esx_adapter_0",
            "vm_physical_path": "/Root/Datacenter/marckluster/marckluster_0",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "fetch_time": "2020-05-13 10:02:45",
            "plugin_type": "Adapter",
            "boot_time": "2018-12-14 14:15:24",
            "network_interfaces": [],
            "plugin_name": "esx_adapter",
            "pretty_id": "AX-49",
            "power_state": "Unknown",
            "cloud_provider": "VMWare",
            "type": "entitydata",
            "os": {
                "distribution": "(?) vmware esxi 6.5.0 build-4564106",
                "os_str": "vmware esxi 6.5.0 build-4564106",
                "type": "VMWare"
            },
            "id": "shit48",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 515,
            "device_type": "ESXHost",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "703e1142-a5ff-6716-ec25-55079c9ce451",
            "name": "marckluster_0",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "system_identifying_info": [],
            "quick_id": "esx_adapter_0!703e1142-a5ff-6716-ec25-55079c9ce451",
            "device_model": "VMware7,1",
            "device_manufacturer": "VMware, Inc.",
            "bios_version": "VMW71.00V.0.B64.1704110547"
        },
        {
            "hostname": "192.168.20.32",
            "cloud_id": "5c911142-9eaf-f932-b2d0-ed6f94a983fc",
            "plugin_unique_name": "esx_adapter_0",
            "vm_physical_path": "/Root/Datacenter/marckluster/marckluster_1",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "fetch_time": "2020-05-13 10:02:45",
            "plugin_type": "Adapter",
            "boot_time": "2018-12-14 14:17:11",
            "network_interfaces": [],
            "plugin_name": "esx_adapter",
            "pretty_id": "AX-50",
            "power_state": "Unknown",
            "cloud_provider": "VMWare",
            "type": "entitydata",
            "os": {
                "distribution": "(?) vmware esxi 6.5.0 build-4564106",
                "os_str": "vmware esxi 6.5.0 build-4564106",
                "type": "VMWare"
            },
            "id": "shit49",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 515,
            "device_type": "ESXHost",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "5c911142-9eaf-f932-b2d0-ed6f94a983fc",
            "name": "marckluster_1",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "system_identifying_info": [],
            "quick_id": "esx_adapter_0!5c911142-9eaf-f932-b2d0-ed6f94a983fc",
            "device_model": "VMware7,1",
            "device_manufacturer": "VMware, Inc.",
            "bios_version": "VMW71.00V.0.B64.1704110547"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 40.0
                }
            ],
            "fetch_time": "2020-05-13 10:02:45",
            "cloud_id": "5011b327-7833-4d80-af9f-11c0afdde448",
            "vm_path_name": "[datastore1] just_for_datacenter_folders/just_for_datacenter_folders.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/mah_folder/Datacenter 2/just_for_datacenter_folders",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ISO [] /vmfs/volumes/9e31cd8e-31c02914/installations/images/windows/en_windows_server_2012_r2_with_update_x64_dvd_6052708.iso"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2017-12-24 17:49:01",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:DE:96",
                    "manufacturer": "VMware (VMware, Inc.)"
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 4.0,
            "esx_host": "192.168.20.12",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsNotInstalled",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 1,
            "os": {
                "distribution": "Server 2012",
                "is_windows_server": true,
                "bitness": 64,
                "type": "Windows",
                "os_str": "microsoft windows server 2012 (64-bit)"
            },
            "id": "shit50",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 870,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "4211ba1c-000b-91a5-8673-14069d093f51",
            "name": "just_for_datacenter_folders",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-51",
            "quick_id": "esx_adapter_0!5011b327-7833-4d80-af9f-11c0afdde448",
            "hds_total": 40.0,
            "last_seen": "2020-05-13 10:02:45"
        },
        {
            "hostname": "192.168.20.12",
            "cloud_id": "d9634d56-0f0b-2470-b00b-36ddb5dd068c",
            "pretty_id": "AX-52",
            "plugin_unique_name": "esx_adapter_0",
            "vm_physical_path": "/Root/mah_folder/Datacenter 2/192.168.20.12",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "fetch_time": "2020-05-13 10:02:45",
            "plugin_type": "Adapter",
            "boot_time": "2017-12-24 17:39:42",
            "network_interfaces": [],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 8.573654174804688,
            "power_state": "Unknown",
            "cloud_provider": "VMWare",
            "type": "entitydata",
            "os": {
                "distribution": "(?) vmware esxi 6.5.0 build-4564106",
                "os_str": "vmware esxi 6.5.0 build-4564106",
                "type": "VMWare"
            },
            "id": "shit51",
            "connection_hostname": "vcenter.axonius.lan",
            "cpus": [
                {
                    "ghz": 2.0478515625,
                    "cores": 4
                }
            ],
            "uptime": 870,
            "device_type": "ESXHost",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "d9634d56-0f0b-2470-b00b-36ddb5dd068c",
            "name": "192.168.20.12",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "system_identifying_info": [],
            "quick_id": "esx_adapter_0!d9634d56-0f0b-2470-b00b-36ddb5dd068c",
            "device_model": "VMware Virtual Platform",
            "device_manufacturer": "VMware, Inc.",
            "bios_version": "6.00"
        },
        {
            "hard_drives": [
                {
                    "device": "Hard disk 1",
                    "total_size": 500.0
                }
            ],
            "hostname": "axonius",
            "cloud_id": "5011b4a1-204b-6f2f-19ec-1bf791cb508b",
            "vm_path_name": "[sata-disk] export-test-1588711354.3538864/export-test-1588711354.3538864.vmx",
            "consolidation_needed": false,
            "vm_physical_path": "/Root/Datacenter/export-test-1588711354.3538864",
            "connected_devices": [],
            "first_fetch_time": "2020-05-13 10:02:45",
            "cd_summaries": [
                "ATAPI CD/DVD drive 0"
            ],
            "plugin_type": "Adapter",
            "boot_time": "2020-05-05 20:44:37",
            "network_interfaces": [
                {
                    "mac": "00:50:56:91:B2:1A",
                    "ips_raw": [
                        3232240676,
                        null
                    ],
                    "manufacturer": "VMware (VMware, Inc.)",
                    "ips": [
                        "192.168.20.36",
                        "fe80::250:56ff:fe91:b21a"
                    ]
                },
                {
                    "mac": "8A:4A:76:34:79:70",
                    "ips_raw": [
                        null
                    ],
                    "ips": [
                        "fe80::884a:76ff:fe34:7970"
                    ]
                },
                {
                    "mac": "CE:4F:50:C9:E4:99",
                    "ips_raw": [
                        null,
                        null
                    ],
                    "ips": [
                        "fe80::cc4f:50ff:fec9:e499",
                        "fe80::cc4f:50ff:fec9:e499"
                    ]
                },
                {
                    "mac": "1A:23:B2:35:91:24",
                    "ips_raw": [
                        null
                    ],
                    "ips": [
                        "fe80::1823:b2ff:fe35:9124"
                    ]
                }
            ],
            "plugin_name": "esx_adapter",
            "total_physical_memory": 32.0,
            "esx_host": "esx.axonius.local",
            "power_state": "TurnedOn",
            "vm_tools_status": "toolsOk",
            "type": "entitydata",
            "plugin_unique_name": "esx_adapter_0",
            "total_number_of_physical_processors": 8,
            "os": {
                "distribution": "Ubuntu",
                "bitness": 64,
                "type": "Linux",
                "os_str": "ubuntu linux (64-bit)"
            },
            "id": "shit52",
            "cloud_provider": "VMWare",
            "connection_hostname": "vcenter.axonius.lan",
            "uptime": 7,
            "device_type": "VMMachine",
            "accurate_for_datetime": "2020-05-13 10:02:45",
            "client_used": "vcenter.axonius.lan/readonly@vsphere.local",
            "uuid": "42118665-5ddd-b015-552a-358e9dfa4903",
            "name": "export-test-1588711354.3538864",
            "adapter_properties": [
                "Assets",
                "Virtualization"
            ],
            "pretty_id": "AX-0",
            "quick_id": "esx_adapter_0!5011b4a1-204b-6f2f-19ec-1bf791cb508b",
            "fetch_time": "2020-05-13 10:02:45",
            "hds_total": 500.0,
            "last_seen": "2020-05-13 10:02:45"
        }
    ],
	"fields": ["connection_hostname","vm_tools_status","vm_physical_path","device_type","esx_host","hds_total","vm_path_name","consolidation_needed","cd_summaries","system_identifying_info","system_identifying_info.key","system_identifying_info.value","name","hostname","last_seen","fetch_time","first_fetch_time","network_interfaces","network_interfaces.name","network_interfaces.mac","network_interfaces.manufacturer","network_interfaces.ips","network_interfaces.subnets","network_interfaces.vlan_list","network_interfaces.vlan_list.name","network_interfaces.vlan_list.tagid","network_interfaces.vlan_list.tagness","network_interfaces.operational_status","network_interfaces.admin_status","network_interfaces.speed","network_interfaces.port_type","network_interfaces.mtu","network_interfaces.gateway","network_interfaces.port","os.type","os.distribution","os.is_windows_server","os.os_str","os.bitness","os.sp","os.install_date","os.kernel_version","os.codename","os.major","os.minor","os.build","os.serial","connected_devices","connected_devices.remote_name","connected_devices.local_ifaces","connected_devices.local_ifaces.name","connected_devices.local_ifaces.mac","connected_devices.local_ifaces.manufacturer","connected_devices.local_ifaces.ips","connected_devices.local_ifaces.subnets","connected_devices.local_ifaces.vlan_list","connected_devices.local_ifaces.vlan_list.name","connected_devices.local_ifaces.vlan_list.tagid","connected_devices.local_ifaces.vlan_list.tagness","connected_devices.local_ifaces.operational_status","connected_devices.local_ifaces.admin_status","connected_devices.local_ifaces.speed","connected_devices.local_ifaces.port_type","connected_devices.local_ifaces.mtu","connected_devices.local_ifaces.gateway","connected_devices.local_ifaces.port","connected_devices.remote_ifaces","connected_devices.remote_ifaces.name","connected_devices.remote_ifaces.mac","connected_devices.remote_ifaces.manufacturer","connected_devices.remote_ifaces.ips","connected_devices.remote_ifaces.subnets","connected_devices.remote_ifaces.vlan_list","connected_devices.remote_ifaces.vlan_list.name","connected_devices.remote_ifaces.vlan_list.tagid","connected_devices.remote_ifaces.vlan_list.tagness","connected_devices.remote_ifaces.operational_status","connected_devices.remote_ifaces.admin_status","connected_devices.remote_ifaces.speed","connected_devices.remote_ifaces.port_type","connected_devices.remote_ifaces.mtu","connected_devices.remote_ifaces.gateway","connected_devices.remote_ifaces.port","connected_devices.connection_type","id","hard_drives","hard_drives.path","hard_drives.device","hard_drives.file_system","hard_drives.total_size","hard_drives.free_size","hard_drives.is_encrypted","hard_drives.description","hard_drives.serial_number","cpus","cpus.name","cpus.manufacturer","cpus.bitness","cpus.family","cpus.cores","cpus.cores_thread","cpus.load_percentage","cpus.architecture","cpus.ghz","boot_time","uptime","device_manufacturer","device_model","bios_version","total_physical_memory","total_number_of_physical_processors","power_state","tags","tags.tag_key","tags.tag_value","cloud_provider","cloud_id","adapter_properties","uuid","adapter_count"],
	"additional_schema": [{"name":"connection_hostname","title":"ESX/VCenter UI Hostname","type":"string"},{"name":"vm_tools_status","title":"VM Tools Status","type":"string"},{"name":"vm_physical_path","title":"VM physical path","type":"string"},{"enum":["ESXHost","VMMachine"],"name":"device_type","title":"VM type","type":"string"},{"name":"esx_host","title":"VM ESX Host","type":"string"},{"name":"hds_total","title":"Total HDs Size (GB)","type":"number"},{"name":"vm_path_name","title":"VM Path Name","type":"string"},{"name":"consolidation_needed","title":"Consolidation Needed","type":"bool"},{"items":{"type":"string"},"name":"cd_summaries","title":"CD/DVD Summaries","type":"array"},{"items":{"items":[{"name":"key","title":"Type","type":"string"},{"name":"value","title":"Value","type":"string"}],"type":"array"},"name":"system_identifying_info","title":"Identifying Info","type":"array"},{"branched":true,"name":"system_identifying_info.key","title":"Identifying Info: Type","type":"string"},{"branched":true,"name":"system_identifying_info.value","title":"Identifying Info: Value","type":"string"},{"name":"name","title":"Asset Name","type":"string"},{"name":"hostname","title":"Host Name","type":"string"},{"format":"date-time","name":"last_seen","title":"Last Seen","type":"string"},{"format":"date-time","name":"fetch_time","title":"Fetch Time","type":"string"},{"format":"date-time","name":"first_fetch_time","title":"First Fetch Time","type":"string"},{"format":"table","items":{"items":[{"name":"name","title":"Iface Name","type":"string"},{"name":"mac","title":"MAC","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"ips","title":"IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"subnets","title":"Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"vlan_list","title":"Vlans","type":"array"},{"branched":true,"name":"vlan_list.name","title":"Vlans: Vlan Name","type":"string"},{"branched":true,"name":"vlan_list.tagid","title":"Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"vlan_list.tagness","title":"Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"operational_status","title":"Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"admin_status","title":"Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"speed","title":"Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"port_type","title":"Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"mtu","title":"MTU","type":"string"},{"name":"gateway","title":"Gateway","type":"string"},{"name":"port","title":"Port","type":"string"}],"type":"array"},"name":"network_interfaces","title":"Network Interfaces","type":"array"},{"branched":true,"name":"network_interfaces.name","title":"Network Interfaces: Iface Name","type":"string"},{"branched":true,"name":"network_interfaces.mac","title":"Network Interfaces: MAC","type":"string"},{"branched":true,"name":"network_interfaces.manufacturer","title":"Network Interfaces: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"network_interfaces.ips","title":"Network Interfaces: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"network_interfaces.subnets","title":"Network Interfaces: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"network_interfaces.vlan_list","title":"Network Interfaces: Vlans","type":"array"},{"branched":true,"name":"network_interfaces.vlan_list.name","title":"Network Interfaces: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"network_interfaces.vlan_list.tagid","title":"Network Interfaces: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"network_interfaces.vlan_list.tagness","title":"Network Interfaces: Vlans: Vlan Tagness","type":"string"},{"branched":true,"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"network_interfaces.operational_status","title":"Network Interfaces: Operational Status","type":"string"},{"branched":true,"enum":["Up","Down","Testing"],"name":"network_interfaces.admin_status","title":"Network Interfaces: Admin Status","type":"string"},{"branched":true,"description":"Interface max speed per Second","name":"network_interfaces.speed","title":"Network Interfaces: Interface Speed","type":"string"},{"branched":true,"enum":["Access","Trunk"],"name":"network_interfaces.port_type","title":"Network Interfaces: Port Type","type":"string"},{"branched":true,"description":"Interface Maximum transmission unit","name":"network_interfaces.mtu","title":"Network Interfaces: MTU","type":"string"},{"branched":true,"name":"network_interfaces.gateway","title":"Network Interfaces: Gateway","type":"string"},{"branched":true,"name":"network_interfaces.port","title":"Network Interfaces: Port","type":"string"},{"enum":["Windows","Linux","OS X","iOS","AirOS","Android","FreeBSD","VMWare","Cisco","Mikrotik","VxWorks","PanOS","F5 Networks Big-IP","Solaris","AIX","Printer","PlayStation","Check Point","Arista","Netscaler"],"name":"os.type","title":"OS: Type","type":"string"},{"name":"os.distribution","title":"OS: Distribution","type":"string"},{"name":"os.is_windows_server","title":"OS: Is Windows Server","type":"bool"},{"name":"os.os_str","title":"OS: Full OS String","type":"string"},{"enum":[32,64],"name":"os.bitness","title":"OS: Bitness","type":"integer"},{"name":"os.sp","title":"OS: Service Pack","type":"string"},{"format":"date-time","name":"os.install_date","title":"OS: Install Date","type":"string"},{"name":"os.kernel_version","title":"OS: Kernel Version","type":"string"},{"name":"os.codename","title":"OS: Code name","type":"string"},{"name":"os.major","title":"OS: Major","type":"integer"},{"name":"os.minor","title":"OS: Minor","type":"integer"},{"name":"os.build","title":"OS: Build","type":"string"},{"name":"os.serial","title":"OS: Serial","type":"string"},{"format":"table","items":{"items":[{"name":"remote_name","title":"Remote Device Name","type":"string"},{"items":{"items":[{"name":"name","title":"Iface Name","type":"string"},{"name":"mac","title":"MAC","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"ips","title":"IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"subnets","title":"Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"vlan_list","title":"Vlans","type":"array"},{"branched":true,"name":"vlan_list.name","title":"Vlans: Vlan Name","type":"string"},{"branched":true,"name":"vlan_list.tagid","title":"Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"vlan_list.tagness","title":"Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"operational_status","title":"Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"admin_status","title":"Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"speed","title":"Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"port_type","title":"Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"mtu","title":"MTU","type":"string"},{"name":"gateway","title":"Gateway","type":"string"},{"name":"port","title":"Port","type":"string"}],"type":"array"},"name":"local_ifaces","title":"Local Interface","type":"array"},{"branched":true,"name":"local_ifaces.name","title":"Local Interface: Iface Name","type":"string"},{"branched":true,"name":"local_ifaces.mac","title":"Local Interface: MAC","type":"string"},{"branched":true,"name":"local_ifaces.manufacturer","title":"Local Interface: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"local_ifaces.ips","title":"Local Interface: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"local_ifaces.subnets","title":"Local Interface: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"local_ifaces.vlan_list","title":"Local Interface: Vlans","type":"array"},{"branched":true,"name":"local_ifaces.vlan_list.name","title":"Local Interface: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"local_ifaces.vlan_list.tagid","title":"Local Interface: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"local_ifaces.vlan_list.tagness","title":"Local Interface: Vlans: Vlan Tagness","type":"string"},{"branched":true,"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"local_ifaces.operational_status","title":"Local Interface: Operational Status","type":"string"},{"branched":true,"enum":["Up","Down","Testing"],"name":"local_ifaces.admin_status","title":"Local Interface: Admin Status","type":"string"},{"branched":true,"description":"Interface max speed per Second","name":"local_ifaces.speed","title":"Local Interface: Interface Speed","type":"string"},{"branched":true,"enum":["Access","Trunk"],"name":"local_ifaces.port_type","title":"Local Interface: Port Type","type":"string"},{"branched":true,"description":"Interface Maximum transmission unit","name":"local_ifaces.mtu","title":"Local Interface: MTU","type":"string"},{"branched":true,"name":"local_ifaces.gateway","title":"Local Interface: Gateway","type":"string"},{"branched":true,"name":"local_ifaces.port","title":"Local Interface: Port","type":"string"},{"items":{"items":[{"name":"name","title":"Iface Name","type":"string"},{"name":"mac","title":"MAC","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"ips","title":"IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"subnets","title":"Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"vlan_list","title":"Vlans","type":"array"},{"branched":true,"name":"vlan_list.name","title":"Vlans: Vlan Name","type":"string"},{"branched":true,"name":"vlan_list.tagid","title":"Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"vlan_list.tagness","title":"Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"operational_status","title":"Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"admin_status","title":"Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"speed","title":"Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"port_type","title":"Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"mtu","title":"MTU","type":"string"},{"name":"gateway","title":"Gateway","type":"string"},{"name":"port","title":"Port","type":"string"}],"type":"array"},"name":"remote_ifaces","title":"Remote Device Iface","type":"array"},{"branched":true,"name":"remote_ifaces.name","title":"Remote Device Iface: Iface Name","type":"string"},{"branched":true,"name":"remote_ifaces.mac","title":"Remote Device Iface: MAC","type":"string"},{"branched":true,"name":"remote_ifaces.manufacturer","title":"Remote Device Iface: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"remote_ifaces.ips","title":"Remote Device Iface: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"remote_ifaces.subnets","title":"Remote Device Iface: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"remote_ifaces.vlan_list","title":"Remote Device Iface: Vlans","type":"array"},{"branched":true,"name":"remote_ifaces.vlan_list.name","title":"Remote Device Iface: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"remote_ifaces.vlan_list.tagid","title":"Remote Device Iface: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"remote_ifaces.vlan_list.tagness","title":"Remote Device Iface: Vlans: Vlan Tagness","type":"string"},{"branched":true,"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"remote_ifaces.operational_status","title":"Remote Device Iface: Operational Status","type":"string"},{"branched":true,"enum":["Up","Down","Testing"],"name":"remote_ifaces.admin_status","title":"Remote Device Iface: Admin Status","type":"string"},{"branched":true,"description":"Interface max speed per Second","name":"remote_ifaces.speed","title":"Remote Device Iface: Interface Speed","type":"string"},{"branched":true,"enum":["Access","Trunk"],"name":"remote_ifaces.port_type","title":"Remote Device Iface: Port Type","type":"string"},{"branched":true,"description":"Interface Maximum transmission unit","name":"remote_ifaces.mtu","title":"Remote Device Iface: MTU","type":"string"},{"branched":true,"name":"remote_ifaces.gateway","title":"Remote Device Iface: Gateway","type":"string"},{"branched":true,"name":"remote_ifaces.port","title":"Remote Device Iface: Port","type":"string"},{"enum":["Direct","Indirect"],"name":"connection_type","title":"Connection Type","type":"string"}],"type":"array"},"name":"connected_devices","title":"Connected Devices","type":"array"},{"branched":true,"name":"connected_devices.remote_name","title":"Connected Devices: Remote Device Name","type":"string"},{"items":{"items":[{"name":"name","title":"Iface Name","type":"string"},{"name":"mac","title":"MAC","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"ips","title":"IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"subnets","title":"Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"vlan_list","title":"Vlans","type":"array"},{"branched":true,"name":"vlan_list.name","title":"Vlans: Vlan Name","type":"string"},{"branched":true,"name":"vlan_list.tagid","title":"Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"vlan_list.tagness","title":"Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"operational_status","title":"Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"admin_status","title":"Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"speed","title":"Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"port_type","title":"Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"mtu","title":"MTU","type":"string"},{"name":"gateway","title":"Gateway","type":"string"},{"name":"port","title":"Port","type":"string"}],"type":"array"},"name":"connected_devices.local_ifaces","title":"Connected Devices: Local Interface","type":"array"},{"branched":true,"name":"connected_devices.local_ifaces.name","title":"Connected Devices: Local Interface: Iface Name","type":"string"},{"branched":true,"name":"connected_devices.local_ifaces.mac","title":"Connected Devices: Local Interface: MAC","type":"string"},{"branched":true,"name":"connected_devices.local_ifaces.manufacturer","title":"Connected Devices: Local Interface: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"connected_devices.local_ifaces.ips","title":"Connected Devices: Local Interface: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"connected_devices.local_ifaces.subnets","title":"Connected Devices: Local Interface: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"connected_devices.local_ifaces.vlan_list","title":"Connected Devices: Local Interface: Vlans","type":"array"},{"branched":true,"name":"connected_devices.local_ifaces.vlan_list.name","title":"Connected Devices: Local Interface: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"connected_devices.local_ifaces.vlan_list.tagid","title":"Connected Devices: Local Interface: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"connected_devices.local_ifaces.vlan_list.tagness","title":"Connected Devices: Local Interface: Vlans: Vlan Tagness","type":"string"},{"branched":true,"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"connected_devices.local_ifaces.operational_status","title":"Connected Devices: Local Interface: Operational Status","type":"string"},{"branched":true,"enum":["Up","Down","Testing"],"name":"connected_devices.local_ifaces.admin_status","title":"Connected Devices: Local Interface: Admin Status","type":"string"},{"branched":true,"description":"Interface max speed per Second","name":"connected_devices.local_ifaces.speed","title":"Connected Devices: Local Interface: Interface Speed","type":"string"},{"branched":true,"enum":["Access","Trunk"],"name":"connected_devices.local_ifaces.port_type","title":"Connected Devices: Local Interface: Port Type","type":"string"},{"branched":true,"description":"Interface Maximum transmission unit","name":"connected_devices.local_ifaces.mtu","title":"Connected Devices: Local Interface: MTU","type":"string"},{"branched":true,"name":"connected_devices.local_ifaces.gateway","title":"Connected Devices: Local Interface: Gateway","type":"string"},{"branched":true,"name":"connected_devices.local_ifaces.port","title":"Connected Devices: Local Interface: Port","type":"string"},{"items":{"items":[{"name":"name","title":"Iface Name","type":"string"},{"name":"mac","title":"MAC","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"ips","title":"IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"subnets","title":"Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"vlan_list","title":"Vlans","type":"array"},{"branched":true,"name":"vlan_list.name","title":"Vlans: Vlan Name","type":"string"},{"branched":true,"name":"vlan_list.tagid","title":"Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"vlan_list.tagness","title":"Vlans: Vlan Tagness","type":"string"},{"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"operational_status","title":"Operational Status","type":"string"},{"enum":["Up","Down","Testing"],"name":"admin_status","title":"Admin Status","type":"string"},{"description":"Interface max speed per Second","name":"speed","title":"Interface Speed","type":"string"},{"enum":["Access","Trunk"],"name":"port_type","title":"Port Type","type":"string"},{"description":"Interface Maximum transmission unit","name":"mtu","title":"MTU","type":"string"},{"name":"gateway","title":"Gateway","type":"string"},{"name":"port","title":"Port","type":"string"}],"type":"array"},"name":"connected_devices.remote_ifaces","title":"Connected Devices: Remote Device Iface","type":"array"},{"branched":true,"name":"connected_devices.remote_ifaces.name","title":"Connected Devices: Remote Device Iface: Iface Name","type":"string"},{"branched":true,"name":"connected_devices.remote_ifaces.mac","title":"Connected Devices: Remote Device Iface: MAC","type":"string"},{"branched":true,"name":"connected_devices.remote_ifaces.manufacturer","title":"Connected Devices: Remote Device Iface: Manufacturer","type":"string"},{"format":"ip","items":{"format":"ip","type":"string"},"name":"connected_devices.remote_ifaces.ips","title":"Connected Devices: Remote Device Iface: IPs","type":"array"},{"description":"A list of subnets in ip format, that correspond the IPs","format":"subnet","items":{"format":"subnet","type":"string"},"name":"connected_devices.remote_ifaces.subnets","title":"Connected Devices: Remote Device Iface: Subnets","type":"array"},{"description":"A list of vlans in this interface","items":{"items":[{"name":"name","title":"Vlan Name","type":"string"},{"name":"tagid","title":"Tag ID","type":"integer"},{"enum":["Tagged","Untagged"],"name":"tagness","title":"Vlan Tagness","type":"string"}],"type":"array"},"name":"connected_devices.remote_ifaces.vlan_list","title":"Connected Devices: Remote Device Iface: Vlans","type":"array"},{"branched":true,"name":"connected_devices.remote_ifaces.vlan_list.name","title":"Connected Devices: Remote Device Iface: Vlans: Vlan Name","type":"string"},{"branched":true,"name":"connected_devices.remote_ifaces.vlan_list.tagid","title":"Connected Devices: Remote Device Iface: Vlans: Tag ID","type":"integer"},{"branched":true,"enum":["Tagged","Untagged"],"name":"connected_devices.remote_ifaces.vlan_list.tagness","title":"Connected Devices: Remote Device Iface: Vlans: Vlan Tagness","type":"string"},{"branched":true,"enum":["Up","Down","Testing","Unknown","Dormant","Nonpresent","LowerLayerDown"],"name":"connected_devices.remote_ifaces.operational_status","title":"Connected Devices: Remote Device Iface: Operational Status","type":"string"},{"branched":true,"enum":["Up","Down","Testing"],"name":"connected_devices.remote_ifaces.admin_status","title":"Connected Devices: Remote Device Iface: Admin Status","type":"string"},{"branched":true,"description":"Interface max speed per Second","name":"connected_devices.remote_ifaces.speed","title":"Connected Devices: Remote Device Iface: Interface Speed","type":"string"},{"branched":true,"enum":["Access","Trunk"],"name":"connected_devices.remote_ifaces.port_type","title":"Connected Devices: Remote Device Iface: Port Type","type":"string"},{"branched":true,"description":"Interface Maximum transmission unit","name":"connected_devices.remote_ifaces.mtu","title":"Connected Devices: Remote Device Iface: MTU","type":"string"},{"branched":true,"name":"connected_devices.remote_ifaces.gateway","title":"Connected Devices: Remote Device Iface: Gateway","type":"string"},{"branched":true,"name":"connected_devices.remote_ifaces.port","title":"Connected Devices: Remote Device Iface: Port","type":"string"},{"branched":true,"enum":["Direct","Indirect"],"name":"connected_devices.connection_type","title":"Connected Devices: Connection Type","type":"string"},{"name":"id","title":"ID","type":"string"},{"format":"table","items":{"items":[{"name":"path","title":"Path","type":"string"},{"name":"device","title":"Device Name","type":"string"},{"name":"file_system","title":"Filesystem","type":"string"},{"name":"total_size","title":"Size (GB)","type":"number"},{"name":"free_size","title":"Free Size (GB)","type":"number"},{"name":"is_encrypted","title":"Encrypted","type":"bool"},{"name":"description","title":"Description","type":"string"},{"name":"serial_number","title":"Serial Number","type":"string"}],"type":"array"},"name":"hard_drives","title":"Hard Drives","type":"array"},{"branched":true,"name":"hard_drives.path","title":"Hard Drives: Path","type":"string"},{"branched":true,"name":"hard_drives.device","title":"Hard Drives: Device Name","type":"string"},{"branched":true,"name":"hard_drives.file_system","title":"Hard Drives: Filesystem","type":"string"},{"branched":true,"name":"hard_drives.total_size","title":"Hard Drives: Size (GB)","type":"number"},{"branched":true,"name":"hard_drives.free_size","title":"Hard Drives: Free Size (GB)","type":"number"},{"branched":true,"name":"hard_drives.is_encrypted","title":"Hard Drives: Encrypted","type":"bool"},{"branched":true,"name":"hard_drives.description","title":"Hard Drives: Description","type":"string"},{"branched":true,"name":"hard_drives.serial_number","title":"Hard Drives: Serial Number","type":"string"},{"items":{"items":[{"name":"name","title":"Description","type":"string"},{"name":"manufacturer","title":"Manufacturer","type":"string"},{"enum":[32,64],"name":"bitness","title":"Bitness","type":"integer"},{"name":"family","title":"Family","type":"string"},{"name":"cores","title":"Cores","type":"integer"},{"name":"cores_thread","title":"Threads in core","type":"integer"},{"name":"load_percentage","title":"Load Percentage","type":"integer"},{"enum":["x86","x64","MIPS","Alpha","PowerPC","ARM","ia64"],"name":"architecture","title":"Architecture","type":"string"},{"name":"ghz","title":"Clockspeed (GHZ)","type":"number"}],"type":"array"},"name":"cpus","title":"CPUs","type":"array"},{"branched":true,"name":"cpus.name","title":"CPUs: Description","type":"string"},{"branched":true,"name":"cpus.manufacturer","title":"CPUs: Manufacturer","type":"string"},{"branched":true,"enum":[32,64],"name":"cpus.bitness","title":"CPUs: Bitness","type":"integer"},{"branched":true,"name":"cpus.family","title":"CPUs: Family","type":"string"},{"branched":true,"name":"cpus.cores","title":"CPUs: Cores","type":"integer"},{"branched":true,"name":"cpus.cores_thread","title":"CPUs: Threads in core","type":"integer"},{"branched":true,"name":"cpus.load_percentage","title":"CPUs: Load Percentage","type":"integer"},{"branched":true,"enum":["x86","x64","MIPS","Alpha","PowerPC","ARM","ia64"],"name":"cpus.architecture","title":"CPUs: Architecture","type":"string"},{"branched":true,"name":"cpus.ghz","title":"CPUs: Clockspeed (GHZ)","type":"number"},{"format":"date-time","name":"boot_time","title":"Boot Time","type":"string"},{"name":"uptime","title":"Uptime (Days)","type":"integer"},{"name":"device_manufacturer","title":"Device Manufacturer","type":"string"},{"name":"device_model","title":"Device Model","type":"string"},{"name":"bios_version","title":"Bios Version","type":"string"},{"name":"total_physical_memory","title":"Total RAM (GB)","type":"number"},{"name":"total_number_of_physical_processors","title":"Total Physical Processors","type":"integer"},{"enum":["TurnedOn","TurnedOff","Suspended","ShuttingDown","Rebooting","StartingUp","Normal","Unknown","Error","Migrating"],"name":"power_state","title":"Power State","type":"string"},{"items":{"items":[{"name":"tag_key","title":"Tag Key","type":"string"},{"name":"tag_value","title":"Tag Value","type":"string"}],"type":"array"},"name":"tags","title":"Adapter Tags","type":"array"},{"branched":true,"name":"tags.tag_key","title":"Adapter Tags: Tag Key","type":"string"},{"branched":true,"name":"tags.tag_value","title":"Adapter Tags: Tag Value","type":"string"},{"name":"cloud_provider","title":"Cloud Provider","type":"string"},{"name":"cloud_id","title":"Cloud ID","type":"string"},{"enum":["Agent","Endpoint_Protection_Platform","Network","Firewall","Manager","Vulnerability_Assessment","Assets","UserManagement","Cloud_Provider","Virtualization","MDM"],"items":{"enum":["Agent","Endpoint_Protection_Platform","Network","Firewall","Manager","Vulnerability_Assessment","Assets","UserManagement","Cloud_Provider","Virtualization","MDM"],"type":"string"},"name":"adapter_properties","title":"Adapter Properties","type":"array"},{"name":"uuid","title":"UUID","type":"string"},{"name":"adapter_count","title":"Distinct Adapter Connections Count","type":"number"}],
	"raw_fields": []
}""")
}
