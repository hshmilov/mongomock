from json_file_adapter.service import FILE_NAME, USERS_DATA, DEVICES_DATA
from test_helpers.file_mock_credentials import FileForCredentialsMock
# pylint: disable=C0302,C0103
wmi_json_file_mock_devices = {
    FILE_NAME: 'WMI_MOCK',
    USERS_DATA: FileForCredentialsMock(USERS_DATA, ''),
    DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, '''{
    "devices": [
        {
            "client_used": "10.20.0.67",
            "plugin_type": "Adapter",
            "plugin_name": "wmi_adapter",
            "plugin_unique_name": "wmi_adapter_0",
            "type": "entitydata",
            "accurate_for_datetime": "2020-06-19 22:36:00",
            "quick_id": "wmi_adapter_0!googlecloud-b59c522b405618e2516573918e3b9727_gcp-dc-test",
            "local_admins_groups": [
                "Organization Management@TESTDOMAIN",
                "Exchange Trusted Subsystem@TESTDOMAIN",
                "Domain Admins@TESTDOMAIN",
                "Enterprise Admins@TESTDOMAIN"
            ],
            "local_admins": [
                {
                    "admin_name": "Organization Management@TESTDOMAIN",
                    "admin_type": "Group Membership"
                },
                {
                    "admin_name": "Exchange Trusted Subsystem@TESTDOMAIN",
                    "admin_type": "Group Membership"
                },
                {
                    "admin_name": "Domain Admins@TESTDOMAIN",
                    "admin_type": "Group Membership"
                },
                {
                    "admin_name": "Enterprise Admins@TESTDOMAIN",
                    "admin_type": "Group Membership"
                },
                {
                    "admin_name": "Administrator@TESTDOMAIN",
                    "admin_type": "Admin User"
                },
                {
                    "admin_name": "avidor@TESTDOMAIN",
                    "admin_type": "Admin User"
                },
                {
                    "admin_name": "ofri@TESTDOMAIN",
                    "admin_type": "Admin User"
                },
                {
                    "admin_name": "mishka@TESTDOMAIN",
                    "admin_type": "Admin User"
                },
                {
                    "admin_name": "db2admin@TESTDOMAIN",
                    "admin_type": "Admin User"
                },
                {
                    "admin_name": "archuser@TESTDOMAIN",
                    "admin_type": "Admin User"
                },
                {
                    "admin_name": "Administrator2@TESTDOMAIN",
                    "admin_type": "Admin User"
                }
            ],
            "local_admins_users": [
                "Administrator@TESTDOMAIN",
                "avidor@TESTDOMAIN",
                "ofri@TESTDOMAIN",
                "mishka@TESTDOMAIN",
                "db2admin@TESTDOMAIN",
                "archuser@TESTDOMAIN",
                "Administrator2@TESTDOMAIN"
            ],
            "users": [
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-501",
                    "username": "Guest@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-502",
                    "username": "krbtgt@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-503",
                    "username": "DefaultAccount@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-1116",
                    "username": "disableduser@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-1137",
                    "username": "$H31000-BI2KN6Q35UUI@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-1138",
                    "username": "SM_bb4c81648cc24bbfa@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-1139",
                    "username": "SM_7b95c7406ada480b9@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-1140",
                    "username": "SM_5f9a36f4ebd642018@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-1141",
                    "username": "SM_d9feae8154a844b79@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-1142",
                    "username": "SM_7e828932f5cf4d038@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-1143",
                    "username": "SM_85db2893d953473a8@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-2601",
                    "username": "SM_6eeb702e306849a49@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-2602",
                    "username": "SM_f6cd93fac79c4ba58@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-2603",
                    "username": "SM_5eea9256c27b4d42a@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-6718",
                    "username": "guestemployee@testdomain.test",
                    "is_local": false,
                    "is_disabled": true,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3314516243-2606363405-3997762602-1000",
                    "username": "Unknown@testdomain.test",
                    "last_use_date": "2020-06-02 20:27:36",
                    "is_local": false,
                    "is_disabled": false,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                },
                {
                    "user_sid": "S-1-5-21-3246437399-2412088855-2625664447-500",
                    "username": "Administrator@TestDomain.test",
                    "last_use_date": "2020-06-21 14:48:43",
                    "is_local": false,
                    "should_create_if_not_exists": true,
                    "creation_source_plugin_type": "Adapter",
                    "creation_source_plugin_name": "wmi_adapter",
                    "creation_source_plugin_unique_name": "wmi_adapter_0"
                }
            ],
            "last_used_users": [
                "Administrator@TestDomain.test"
            ],
            "software_cves": [],
            "installed_software": [
                {
                    "name_version": "GooGet - google-compute-engine-metadata-scripts-20200129.00.0@1",
                    "name": "GooGet - google-compute-engine-metadata-scripts",
                    "version": "20200129.00.0@1"
                },
                {
                    "vendor": "Google Inc.",
                    "name": "Google Cloud SDK"
                },
                {
                    "name_version": "GooGet - google-compute-engine-driver-netkvm-16.1.3@18",
                    "name": "GooGet - google-compute-engine-driver-netkvm",
                    "version": "16.1.3@18"
                },
                {
                    "name_version": "GooGet - google-osconfig-agent-20200416.00.0@1",
                    "name": "GooGet - google-osconfig-agent",
                    "version": "20200416.00.0@1"
                },
                {
                    "name_version": "GooGet - google-compute-engine-windows-20200529.00.0@1",
                    "name": "GooGet - google-compute-engine-windows",
                    "version": "20200529.00.0@1"
                },
                {
                    "name_version": "GooGet - google-compute-engine-vss-1.1.2@18",
                    "name": "GooGet - google-compute-engine-vss",
                    "version": "1.1.2@18"
                },
                {
                    "name_version": "GooGet - google-compute-engine-driver-vioscsi-16.1.3@18",
                    "name": "GooGet - google-compute-engine-driver-vioscsi",
                    "version": "16.1.3@18"
                },
                {
                    "name_version": "GooGet - google-compute-engine-driver-pvpanic-16.1.3@18",
                    "name": "GooGet - google-compute-engine-driver-pvpanic",
                    "version": "16.1.3@18"
                },
                {
                    "name_version": "GooGet - google-compute-engine-auto-updater-1.2.1@1",
                    "name": "GooGet - google-compute-engine-auto-updater",
                    "version": "1.2.1@1"
                },
                {
                    "name_version": "GooGet - googet-2.17.0@1",
                    "name": "GooGet - googet",
                    "version": "2.17.0@1"
                },
                {
                    "name_version": "GooGet - google-compute-engine-driver-gvnic-0.9.5@24",
                    "name": "GooGet - google-compute-engine-driver-gvnic",
                    "version": "0.9.5@24"
                },
                {
                    "name_version": "GooGet - google-compute-engine-sysprep-3.11.1@1",
                    "name": "GooGet - google-compute-engine-sysprep",
                    "version": "3.11.1@1"
                },
                {
                    "name_version": "GooGet - google-compute-engine-driver-balloon-16.1.3@18",
                    "name": "GooGet - google-compute-engine-driver-balloon",
                    "version": "16.1.3@18"
                },
                {
                    "name_version": "GooGet - google-compute-engine-driver-gga-1.1.1@18",
                    "name": "GooGet - google-compute-engine-driver-gga",
                    "version": "1.1.1@18"
                }
            ],
            "cpus": [
                {
                    "name": "Intel(R) Xeon(R) CPU @ 2.30GHz",
                    "bitness": 64,
                    "cores": 2,
                    "load_percentage": 48,
                    "architecture": "x64",
                    "ghz": 2.25
                }
            ],
            "bios_version": "Google",
            "bios_serial": "googlecloud-b59c522b405618e2516573918e3b9727",
            "device_model": "Google Compute Engine",
            "device_manufacturer": "Google",
            "hostname": "gcp-dc-test",
            "total_number_of_physical_processors": 1,
            "total_number_of_cores": 4,
            "domain": "TestDomain.test",
            "part_of_domain": true,
            "pc_type": "Desktop",
            "device_serial": "Board-GoogleCloud-B59C522B405618E2516573918E3B9727",
            "os": {
                "type": "Windows",
                "distribution": "Server 2016",
                "os_str": "microsoft windows server 2016 datacenter",
                "is_windows_server": true,
                "install_date": "2020-06-02 20:18:20",
                "major": 10,
                "minor": 0,
                "build": "14393"
            },
            "boot_time": "2020-06-02 20:52:10",
            "uptime": 17,
            "total_physical_memory": 16.0,
            "free_physical_memory": 13.25,
            "physical_memory_percentage": 17.16,
            "number_of_processes": 54,
            "hard_drives": [
                {
                    "path": "C:",
                    "total_size": 99.88669967651367,
                    "free_size": 79.99118041992188,
                    "file_system": "NTFS"
                }
            ],
            "security_patches": [
                {
                    "security_patch_id": "KB4552926",
                    "installed_on": "2020-05-13 00:00:00"
                },
                {
                    "security_patch_id": "KB4049065",
                    "installed_on": "2018-02-02 00:00:00"
                },
                {
                    "security_patch_id": "KB4486129",
                    "installed_on": "2020-05-13 00:00:00"
                },
                {
                    "security_patch_id": "KB4494175",
                    "installed_on": "2020-05-13 00:00:00"
                },
                {
                    "security_patch_id": "KB4524244",
                    "installed_on": "2020-05-13 00:00:00"
                },
                {
                    "security_patch_id": "KB4550994",
                    "installed_on": "2020-05-13 00:00:00"
                },
                {
                    "security_patch_id": "KB4562561",
                    "installed_on": "2020-06-10 00:00:00"
                },
                {
                    "security_patch_id": "KB4556813",
                    "installed_on": "2020-05-13 00:00:00"
                },
                {
                    "security_patch_id": "KB4561616"
                }
            ],
            "time_zone": "(UTC+00:00) Monrovia, Reykjavik",
            "network_interfaces": [
                {
                    "mac": "42:01:0A:14:00:43",
                    "ips": [
                        "10.20.0.67",
                        "fe80::47b:17f6:6ccd:ecce"
                    ],
                    "ips_raw": [
                        169082947,
                        null
                    ]
                }
            ],
            "processes": [
                {
                    "name": "System Idle Process"
                },
                {
                    "name": "System"
                },
                {
                    "name": "smss.exe"
                },
                {
                    "name": "csrss.exe"
                },
                {
                    "name": "csrss.exe"
                },
                {
                    "name": "wininit.exe"
                },
                {
                    "name": "winlogon.exe"
                },
                {
                    "name": "services.exe"
                },
                {
                    "name": "lsass.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "LogonUI.exe"
                },
                {
                    "name": "dwm.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "google_osconfig_agent.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "GCEWindowsAgent.exe"
                },
                {
                    "name": "spoolsv.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "dns.exe"
                },
                {
                    "name": "Microsoft.ActiveDirectory.WebServices.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "dllhost.exe"
                },
                {
                    "name": "ismserv.exe"
                },
                {
                    "name": "dfsrs.exe"
                },
                {
                    "name": "GoogleVssAgent.exe"
                },
                {
                    "name": "dfssvc.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "dllhost.exe"
                },
                {
                    "name": "msdtc.exe"
                },
                {
                    "name": "vds.exe"
                },
                {
                    "name": "csrss.exe"
                },
                {
                    "name": "winlogon.exe"
                },
                {
                    "name": "dwm.exe"
                },
                {
                    "name": "rdpclip.exe"
                },
                {
                    "name": "RuntimeBroker.exe"
                },
                {
                    "name": "sihost.exe"
                },
                {
                    "name": "svchost.exe"
                },
                {
                    "name": "taskhostw.exe"
                },
                {
                    "name": "MsMpEng.exe"
                },
                {
                    "name": "NisSrv.exe"
                },
                {
                    "name": "ShellExperienceHost.exe"
                },
                {
                    "name": "SearchUI.exe"
                },
                {
                    "name": "MpCmdRun.exe"
                },
                {
                    "name": "WmiPrvSE.exe"
                },
                {
                    "name": "WmiPrvSE.exe"
                }
            ],
            "services": [
                {
                    "name": "ADWS",
                    "start_name": "LocalSystem",
                    "display_name": "Active Directory Web Services",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\ADWS\\Microsoft.ActiveDirectory.WebServices.exe",
                    "description": "This service provides a Web Service interface to instances of the directory service (AD DS and AD LDS) that are running locally on this server. If this service is stopped or disabled, client applications, such as Active Directory PowerShell, will not be able to access or manage any directory service instances that are running locally on this server.",
                    "caption": "Active Directory Web Services"
                },
                {
                    "name": "AJRouter",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "AllJoyn Router Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Routes AllJoyn messages for the local AllJoyn clients. If this service is stopped the AllJoyn clients that do not have their own bundled routers will be unable to run.",
                    "caption": "AllJoyn Router Service"
                },
                {
                    "name": "ALG",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Application Layer Gateway Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\alg.exe",
                    "description": "Provides support for 3rd party protocol plug-ins for Internet Connection Sharing",
                    "caption": "Application Layer Gateway Service"
                },
                {
                    "name": "AppIDSvc",
                    "start_name": "NT Authority\\LocalService",
                    "display_name": "Application Identity",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Determines and verifies the identity of an application. Disabling this service will prevent AppLocker from being enforced.",
                    "caption": "Application Identity"
                },
                {
                    "name": "Appinfo",
                    "start_name": "LocalSystem",
                    "display_name": "Application Information",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Facilitates the running of interactive applications with additional administrative privileges.  If this service is stopped, users will be unable to launch applications with the additional administrative privileges they may require to perform desired user tasks.",
                    "caption": "Application Information"
                },
                {
                    "name": "AppMgmt",
                    "start_name": "LocalSystem",
                    "display_name": "Application Management",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Processes installation, removal, and enumeration requests for software deployed through Group Policy. If the service is disabled, users will be unable to install, remove, or enumerate software deployed through Group Policy. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Application Management"
                },
                {
                    "name": "AppReadiness",
                    "start_name": "LocalSystem",
                    "display_name": "App Readiness",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k AppReadiness",
                    "description": "Gets apps ready for use the first time a user signs in to this PC and when adding new apps.",
                    "caption": "App Readiness"
                },
                {
                    "name": "AppVClient",
                    "start_name": "LocalSystem",
                    "display_name": "Microsoft App-V Client",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\AppVClient.exe",
                    "description": "Manages App-V users and virtual applications",
                    "caption": "Microsoft App-V Client"
                },
                {
                    "name": "AppXSvc",
                    "start_name": "LocalSystem",
                    "display_name": "AppX Deployment Service (AppXSVC)",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k wsappx",
                    "description": "Provides infrastructure support for deploying Store applications. This service is started on demand and if disabled Store applications will not be deployed to the system, and may not function properly.",
                    "caption": "AppX Deployment Service (AppXSVC)"
                },
                {
                    "name": "AudioEndpointBuilder",
                    "start_name": "LocalSystem",
                    "display_name": "Windows Audio Endpoint Builder",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Manages audio devices for the Windows Audio service.  If this service is stopped, audio devices and effects will not function properly.  If this service is disabled, any services that explicitly depend on it will fail to start",
                    "caption": "Windows Audio Endpoint Builder"
                },
                {
                    "name": "Audiosrv",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Windows Audio",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Manages audio for Windows-based programs.  If this service is stopped, audio devices and effects will not function properly.  If this service is disabled, any services that explicitly depend on it will fail to start",
                    "caption": "Windows Audio"
                },
                {
                    "name": "AxInstSV",
                    "start_name": "LocalSystem",
                    "display_name": "ActiveX Installer (AxInstSV)",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k AxInstSVGroup",
                    "description": "Provides User Account Control validation for the installation of ActiveX controls from the Internet and enables management of ActiveX control installation based on Group Policy settings. This service is started on demand and if disabled the installation of ActiveX controls will behave according to default browser settings.",
                    "caption": "ActiveX Installer (AxInstSV)"
                },
                {
                    "name": "BFE",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Base Filtering Engine",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNoNetwork",
                    "description": "The Base Filtering Engine (BFE) is a service that manages firewall and Internet Protocol security (IPsec) policies and implements user mode filtering. Stopping or disabling the BFE service will significantly reduce the security of the system. It will also result in unpredictable behavior in IPsec management and firewall applications.",
                    "caption": "Base Filtering Engine"
                },
                {
                    "name": "BITS",
                    "start_name": "LocalSystem",
                    "display_name": "Background Intelligent Transfer Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "Transfers files in the background using idle network bandwidth. If the service is disabled, then any applications that depend on BITS, such as Windows Update or MSN Explorer, will be unable to automatically download programs and other information.",
                    "caption": "Background Intelligent Transfer Service"
                },
                {
                    "name": "BrokerInfrastructure",
                    "start_name": "LocalSystem",
                    "display_name": "Background Tasks Infrastructure Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k DcomLaunch",
                    "description": "Windows infrastructure service that controls which background tasks can run on the system.",
                    "caption": "Background Tasks Infrastructure Service"
                },
                {
                    "name": "Browser",
                    "start_name": "LocalSystem",
                    "display_name": "Computer Browser",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k smbsvcs",
                    "description": "Maintains an updated list of computers on the network and supplies this list to computers designated as browsers. If this service is stopped, this list will not be updated or maintained. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Computer Browser"
                },
                {
                    "name": "bthserv",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Bluetooth Support Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "The Bluetooth service supports discovery and association of remote Bluetooth devices.  Stopping or disabling this service may cause already installed Bluetooth devices to fail to operate properly and prevent new devices from being discovered or associated.",
                    "caption": "Bluetooth Support Service"
                },
                {
                    "name": "CDPSvc",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Connected Devices Platform Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "This service is used for Connected Devices and Universal Glass scenarios",
                    "caption": "Connected Devices Platform Service"
                },
                {
                    "name": "CertPropSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Certificate Propagation",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Copies user certificates and root certificates from smart cards into the current user's certificate store, detects when a smart card is inserted into a smart card reader, and, if needed, installs the smart card Plug and Play minidriver.",
                    "caption": "Certificate Propagation"
                },
                {
                    "name": "ClipSVC",
                    "start_name": "LocalSystem",
                    "display_name": "Client License Service (ClipSVC)",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k wsappx",
                    "description": "Provides infrastructure support for the Microsoft Store. This service is started on demand and if disabled applications bought using Windows Store will not behave correctly.",
                    "caption": "Client License Service (ClipSVC)"
                },
                {
                    "name": "COMSysApp",
                    "start_name": "LocalSystem",
                    "display_name": "COM+ System Application",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\dllhost.exe /Processid:{02D4B3F1-FD88-11D1-960D-00805FC79235}",
                    "description": "Manages the configuration and tracking of Component Object Model (COM)+-based components. If the service is stopped, most COM+-based components will not function properly. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "COM+ System Application"
                },
                {
                    "name": "CoreMessagingRegistrar",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "CoreMessaging",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNoNetwork",
                    "description": "Manages communication between system components.",
                    "caption": "CoreMessaging"
                },
                {
                    "name": "CryptSvc",
                    "start_name": "NT Authority\\NetworkService",
                    "display_name": "Cryptographic Services",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k NetworkService",
                    "description": "Provides three management services: Catalog Database Service, which confirms the signatures of Windows files and allows new programs to be installed; Protected Root Service, which adds and removes Trusted Root Certification Authority certificates from this computer; and Automatic Root Certificate Update Service, which retrieves root certificates from Windows Update and enable scenarios such as SSL. If this service is stopped, these management services will not function properly. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Cryptographic Services"
                },
                {
                    "name": "CscService",
                    "start_name": "LocalSystem",
                    "display_name": "Offline Files",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "The Offline Files service performs maintenance activities on the Offline Files cache, responds to user logon and logoff events, implements the internals of the public API, and dispatches interesting events to those interested in Offline Files activities and changes in cache state.",
                    "caption": "Offline Files"
                },
                {
                    "name": "DcomLaunch",
                    "start_name": "LocalSystem",
                    "display_name": "DCOM Server Process Launcher",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k DcomLaunch",
                    "description": "The DCOMLAUNCH service launches COM and DCOM servers in response to object activation requests. If this service is stopped or disabled, programs using COM or DCOM will not function properly. It is strongly recommended that you have the DCOMLAUNCH service running.",
                    "caption": "DCOM Server Process Launcher"
                },
                {
                    "name": "DcpSvc",
                    "start_name": "LocalSystem",
                    "display_name": "DataCollectionPublishingService",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "The DCP (Data Collection and Publishing) service supports first party apps to upload data to cloud.",
                    "caption": "DataCollectionPublishingService"
                },
                {
                    "name": "defragsvc",
                    "start_name": "localSystem",
                    "display_name": "Optimize drives",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k defragsvc",
                    "description": "Helps the computer run more efficiently by optimizing files on storage drives.",
                    "caption": "Optimize drives"
                },
                {
                    "name": "DeviceAssociationService",
                    "start_name": "LocalSystem",
                    "display_name": "Device Association Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Enables pairing between the system and wired or wireless devices.",
                    "caption": "Device Association Service"
                },
                {
                    "name": "DeviceInstall",
                    "start_name": "LocalSystem",
                    "display_name": "Device Install Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k DcomLaunch",
                    "description": "Enables a computer to recognize and adapt to hardware changes with little or no user input. Stopping or disabling this service will result in system instability.",
                    "caption": "Device Install Service"
                },
                {
                    "name": "DevQueryBroker",
                    "start_name": "LocalSystem",
                    "display_name": "DevQuery Background Discovery Broker",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Enables apps to discover devices with a backgroud task",
                    "caption": "DevQuery Background Discovery Broker"
                },
                {
                    "name": "Dfs",
                    "start_name": "LocalSystem",
                    "display_name": "DFS Namespace",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\dfssvc.exe",
                    "description": "Enables you to group shared folders located on different servers into one or more logically structured namespaces. Each namespace appears to users as a single shared folder with a series of subfolders.",
                    "caption": "DFS Namespace"
                },
                {
                    "name": "DFSR",
                    "start_name": "LocalSystem",
                    "display_name": "DFS Replication",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\DFSRs.exe",
                    "description": "Enables you to synchronize folders on multiple servers across local or wide area network (WAN) network connections. This service uses the Remote Differential Compression (RDC) protocol to update only the portions of files that have changed since the last replication.",
                    "caption": "DFS Replication"
                },
                {
                    "name": "Dhcp",
                    "start_name": "NT Authority\\LocalService",
                    "display_name": "DHCP Client",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Registers and updates IP addresses and DNS records for this computer. If this service is stopped, this computer will not receive dynamic IP addresses and DNS updates. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "DHCP Client"
                },
                {
                    "name": "diagnosticshub.standardcollector.service",
                    "start_name": "LocalSystem",
                    "display_name": "Microsoft (R) Diagnostics Hub Standard Collector Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\DiagSvcs\\DiagnosticsHub.StandardCollector.Service.exe",
                    "description": "Diagnostics Hub Standard Collector Service. When running, this service collects real time ETW events and processes them.",
                    "caption": "Microsoft (R) Diagnostics Hub Standard Collector Service"
                },
                {
                    "name": "DiagTrack",
                    "start_name": "LocalSystem",
                    "display_name": "Connected User Experiences and Telemetry",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k utcsvc",
                    "description": "The Connected User Experiences and Telemetry service enables features that support in-application and connected user experiences. Additionally, this service manages the event driven collection and transmission of diagnostic and usage information (used to improve the experience and quality of the Windows Platform) when the diagnostics and usage privacy option settings are enabled under Feedback and Diagnostics.",
                    "caption": "Connected User Experiences and Telemetry"
                },
                {
                    "name": "DmEnrollmentSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Device Management Enrollment Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Performs Device Enrollment Activities for Device Management",
                    "caption": "Device Management Enrollment Service"
                },
                {
                    "name": "dmwappushservice",
                    "start_name": "LocalSystem",
                    "display_name": "dmwappushsvc",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "WAP Push Message Routing Service",
                    "caption": "dmwappushsvc"
                },
                {
                    "name": "DNS",
                    "start_name": "LocalSystem",
                    "display_name": "DNS Server",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\dns.exe",
                    "description": "Enables DNS clients to resolve DNS names by answering DNS queries and dynamic DNS update requests. If this service is stopped, DNS updates will not occur. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "DNS Server"
                },
                {
                    "name": "Dnscache",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "DNS Client",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k NetworkService",
                    "description": "The DNS Client service (dnscache) caches Domain Name System (DNS) names and registers the full computer name for this computer. If the service is stopped, DNS names will continue to be resolved. However, the results of DNS name queries will not be cached and the computer's name will not be registered. If the service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "DNS Client"
                },
                {
                    "name": "dot3svc",
                    "start_name": "localSystem",
                    "display_name": "Wired AutoConfig",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "The Wired AutoConfig (DOT3SVC) service is responsible for performing IEEE 802.1X authentication on Ethernet interfaces. If your current wired network deployment enforces 802.1X authentication, the DOT3SVC service should be configured to run for establishing Layer 2 connectivity and/or providing access to network resources. Wired networks that do not enforce 802.1X authentication are unaffected by the DOT3SVC service.",
                    "caption": "Wired AutoConfig"
                },
                {
                    "name": "DPS",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Diagnostic Policy Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalServiceNoNetwork",
                    "description": "The Diagnostic Policy Service enables problem detection, troubleshooting and resolution for Windows components.  If this service is stopped, diagnostics will no longer function.",
                    "caption": "Diagnostic Policy Service"
                },
                {
                    "name": "DsmSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Device Setup Manager",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Enables the detection, download and installation of device-related software. If this service is disabled, devices may be configured with outdated software, and may not work correctly.",
                    "caption": "Device Setup Manager"
                },
                {
                    "name": "DsRoleSvc",
                    "start_name": "LocalSystem",
                    "display_name": "DS Role Server",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\lsass.exe",
                    "description": "This service hosts the DS Role Server used for DC promotion, demotion, and cloning. If this service is disabled, these operations will fail.",
                    "caption": "DS Role Server"
                },
                {
                    "name": "DsSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Data Sharing Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Provides data brokering between applications.",
                    "caption": "Data Sharing Service"
                },
                {
                    "name": "Eaphost",
                    "start_name": "localSystem",
                    "display_name": "Extensible Authentication Protocol",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "The Extensible Authentication Protocol (EAP) service provides network authentication in such scenarios as 802.1x wired and wireless, VPN, and Network Access Protection (NAP).  EAP also provides application programming interfaces (APIs) that are used by network access clients, including wireless and VPN clients, during the authentication process.  If you disable this service, this computer is prevented from accessing networks that require EAP authentication.",
                    "caption": "Extensible Authentication Protocol"
                },
                {
                    "name": "EFS",
                    "start_name": "LocalSystem",
                    "display_name": "Encrypting File System (EFS)",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\lsass.exe",
                    "description": "Provides the core file encryption technology used to store encrypted files on NTFS file system volumes. If this service is stopped or disabled, applications will be unable to access encrypted files.",
                    "caption": "Encrypting File System (EFS)"
                },
                {
                    "name": "embeddedmode",
                    "start_name": "LocalSystem",
                    "display_name": "Embedded Mode",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "The Embedded Mode service enables scenarios related to Background Applications.  Disabling this service will prevent Background Applications from being activated.",
                    "caption": "Embedded Mode"
                },
                {
                    "name": "EntAppSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Enterprise App Management Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k appmodel",
                    "description": "Enables enterprise application management.",
                    "caption": "Enterprise App Management Service"
                },
                {
                    "name": "EventLog",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Windows Event Log",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "This service manages events and event logs. It supports logging events, querying events, subscribing to events, archiving event logs, and managing event metadata. It can display events in both XML and plain text format. Stopping this service may compromise security and reliability of the system.",
                    "caption": "Windows Event Log"
                },
                {
                    "name": "EventSystem",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "COM+ Event System",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "Supports System Event Notification Service (SENS), which provides automatic distribution of events to subscribing Component Object Model (COM) components. If the service is stopped, SENS will close and will not be able to provide logon and logoff notifications. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "COM+ Event System"
                },
                {
                    "name": "fdPHost",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Function Discovery Provider Host",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "The FDPHOST service hosts the Function Discovery (FD) network discovery providers. These FD providers supply network discovery services for the Simple Services Discovery Protocol (SSDP) and Web Services – Discovery (WS-D) protocol. Stopping or disabling the FDPHOST service will disable network discovery for these protocols when using FD. When this service is unavailable, network services using FD and relying on these discovery protocols will be unable to find network devices or resources.",
                    "caption": "Function Discovery Provider Host"
                },
                {
                    "name": "FDResPub",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Function Discovery Resource Publication",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceAndNoImpersonation",
                    "description": "Publishes this computer and resources attached to this computer so they can be discovered over the network.  If this service is stopped, network resources will no longer be published and they will not be discovered by other computers on the network.",
                    "caption": "Function Discovery Resource Publication"
                },
                {
                    "name": "FontCache",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Windows Font Cache Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "Optimizes performance of applications by caching commonly used font data. Applications will start this service if it is not already running. It can be disabled, though doing so will degrade application performance.",
                    "caption": "Windows Font Cache Service"
                },
                {
                    "name": "FrameServer",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Windows Camera Frame Server",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k Camera",
                    "description": "Enables multiple clients to access video frames from camera devices.",
                    "caption": "Windows Camera Frame Server"
                },
                {
                    "name": "GCEAgent",
                    "start_name": "LocalSystem",
                    "display_name": "Google Compute Engine Agent",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "\"C:\\Program Files\\Google\\Compute Engine\\agent\\GCEWindowsAgent.exe\"",
                    "description": "Google Compute Engine Agent",
                    "caption": "Google Compute Engine Agent"
                },
                {
                    "name": "GoogleVssAgent",
                    "start_name": "LocalSystem",
                    "display_name": "GoogleVssAgent",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "\"C:\\Program Files\\Google\\Compute Engine\\vss\\GoogleVssAgent.exe\"",
                    "description": "Google Vss Agent.",
                    "caption": "GoogleVssAgent"
                },
                {
                    "name": "GoogleVssProvider",
                    "start_name": "LocalSystem",
                    "display_name": "GoogleVssProvider",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\dllhost.exe /Processid:{222E8C6A-7C6D-4335-B169-63C3AE2FEA0A}",
                    "description": "Google Vss Hardware Provider",
                    "caption": "GoogleVssProvider"
                },
                {
                    "name": "google_osconfig_agent",
                    "start_name": "LocalSystem",
                    "display_name": "Google OSConfig Agent",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "\"C:\\Program Files\\Google\\OSConfig\\google_osconfig_agent.exe\"",
                    "description": "Google OSConfig service agent",
                    "caption": "Google OSConfig Agent"
                },
                {
                    "name": "gpsvc",
                    "start_name": "LocalSystem",
                    "display_name": "Group Policy Client",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "The service is responsible for applying settings configured by administrators for the computer and users through the Group Policy component. If the service is disabled, the settings will not be applied and applications and components will not be manageable through Group Policy. Any components or applications that depend on the Group Policy component might not be functional if the service is disabled.",
                    "caption": "Group Policy Client"
                },
                {
                    "name": "hidserv",
                    "start_name": "LocalSystem",
                    "display_name": "Human Interface Device Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Activates and maintains the use of hot buttons on keyboards, remote controls, and other multimedia devices. It is recommended that you keep this service running.",
                    "caption": "Human Interface Device Service"
                },
                {
                    "name": "HvHost",
                    "start_name": "LocalSystem",
                    "display_name": "HV Host Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Provides an interface for the Hyper-V hypervisor to provide per-partition performance counters to the host operating system.",
                    "caption": "HV Host Service"
                },
                {
                    "name": "icssvc",
                    "start_name": "NT Authority\\LocalService",
                    "display_name": "Windows Mobile Hotspot Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Provides the ability to share a cellular data connection with another device.",
                    "caption": "Windows Mobile Hotspot Service"
                },
                {
                    "name": "IKEEXT",
                    "start_name": "LocalSystem",
                    "display_name": "IKE and AuthIP IPsec Keying Modules",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "The IKEEXT service hosts the Internet Key Exchange (IKE) and Authenticated Internet Protocol (AuthIP) keying modules. These keying modules are used for authentication and key exchange in Internet Protocol security (IPsec). Stopping or disabling the IKEEXT service will disable IKE and AuthIP key exchange with peer computers. IPsec is typically configured to use IKE or AuthIP; therefore, stopping or disabling the IKEEXT service might result in an IPsec failure and might compromise the security of the system. It is strongly recommended that you have the IKEEXT service running.",
                    "caption": "IKE and AuthIP IPsec Keying Modules"
                },
                {
                    "name": "iphlpsvc",
                    "start_name": "LocalSystem",
                    "display_name": "IP Helper",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k NetSvcs",
                    "description": "Provides tunnel connectivity using IPv6 transition technologies (6to4, ISATAP, Port Proxy, and Teredo), and IP-HTTPS. If this service is stopped, the computer will not have the enhanced connectivity benefits that these technologies offer.",
                    "caption": "IP Helper"
                },
                {
                    "name": "IsmServ",
                    "start_name": "LocalSystem",
                    "display_name": "Intersite Messaging",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\ismserv.exe",
                    "description": "Enables messages to be exchanged between computers running Windows Server sites. If this service is stopped, messages will not be exchanged, nor will site routing information be calculated for other services.  If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Intersite Messaging"
                },
                {
                    "name": "Kdc",
                    "start_name": "LocalSystem",
                    "display_name": "Kerberos Key Distribution Center",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\lsass.exe",
                    "description": "This service, running on domain controllers, enables users to log on to the network using the Kerberos authentication protocol. If this service is stopped, users will be unable to log on to the network. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Kerberos Key Distribution Center"
                },
                {
                    "name": "KdsSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Microsoft Key Distribution Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\lsass.exe",
                    "description": "This service is used to protect data through the Group Data Protection API. It is also used to support a number of system features including BitLocker on clustered volumes, Managed Service Accounts, and secure DNS. If this service is stopped, those features will no longer work.",
                    "caption": "Microsoft Key Distribution Service"
                },
                {
                    "name": "KeyIso",
                    "start_name": "LocalSystem",
                    "display_name": "CNG Key Isolation",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\lsass.exe",
                    "description": "The CNG key isolation service is hosted in the LSA process. The service provides key process isolation to private keys and associated cryptographic operations as required by the Common Criteria. The service stores and uses long-lived keys in a secure process complying with Common Criteria requirements.",
                    "caption": "CNG Key Isolation"
                },
                {
                    "name": "KPSSVC",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "KDC Proxy Server service (KPS)",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k KpsSvcGroup",
                    "description": "KDC Proxy Server service runs on edge servers to proxy Kerberos protocol messages to domain controllers on the corporate network.",
                    "caption": "KDC Proxy Server service (KPS)"
                },
                {
                    "name": "KtmRm",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "KtmRm for Distributed Transaction Coordinator",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k NetworkServiceAndNoImpersonation",
                    "description": "Coordinates transactions between the Distributed Transaction Coordinator (MSDTC) and the Kernel Transaction Manager (KTM). If it is not needed, it is recommended that this service remain stopped. If it is needed, both MSDTC and KTM will start this service automatically. If this service is disabled, any MSDTC transaction interacting with a Kernel Resource Manager will fail and any services that explicitly depend on it will fail to start.",
                    "caption": "KtmRm for Distributed Transaction Coordinator"
                },
                {
                    "name": "LanmanServer",
                    "start_name": "LocalSystem",
                    "display_name": "Server",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k smbsvcs",
                    "description": "Supports file, print, and named-pipe sharing over the network for this computer. If this service is stopped, these functions will be unavailable. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Server"
                },
                {
                    "name": "LanmanWorkstation",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Workstation",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k NetworkService",
                    "description": "Creates and maintains client network connections to remote servers using the SMB protocol. If this service is stopped, these connections will be unavailable. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Workstation"
                },
                {
                    "name": "lfsvc",
                    "start_name": "LocalSystem",
                    "display_name": "Geolocation Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "This service monitors the current location of the system and manages geofences (a geographical location with associated events).  If you turn off this service, applications will be unable to use or receive notifications for geolocation or geofences.",
                    "caption": "Geolocation Service"
                },
                {
                    "name": "LicenseManager",
                    "start_name": "NT Authority\\LocalService",
                    "display_name": "Windows License Manager Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalService",
                    "description": "Provides infrastructure support for the Windows Store.  This service is started on demand and if disabled then content acquired through the Windows Store will not function properly.",
                    "caption": "Windows License Manager Service"
                },
                {
                    "name": "lltdsvc",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Link-Layer Topology Discovery Mapper",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalService",
                    "description": "Creates a Network Map, consisting of PC and device topology (connectivity) information, and metadata describing each PC and device.  If this service is disabled, the Network Map will not function properly.",
                    "caption": "Link-Layer Topology Discovery Mapper"
                },
                {
                    "name": "lmhosts",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "TCP/IP NetBIOS Helper",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Provides support for the NetBIOS over TCP/IP (NetBT) service and NetBIOS name resolution for clients on the network, therefore enabling users to share files, print, and log on to the network. If this service is stopped, these functions might be unavailable. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "TCP/IP NetBIOS Helper"
                },
                {
                    "name": "LSM",
                    "start_name": "LocalSystem",
                    "display_name": "Local Session Manager",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k DcomLaunch",
                    "description": "Core Windows Service that manages local user sessions. Stopping or disabling this service will result in system instability.",
                    "caption": "Local Session Manager"
                },
                {
                    "name": "MapsBroker",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Downloaded Maps Manager",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k NetworkService",
                    "description": "Windows service for application access to downloaded maps. This service is started on-demand by application accessing downloaded maps. Disabling this service will prevent apps from accessing maps.",
                    "caption": "Downloaded Maps Manager"
                },
                {
                    "name": "MpsSvc",
                    "start_name": "NT Authority\\LocalService",
                    "display_name": "Windows Firewall",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNoNetwork",
                    "description": "Windows Firewall helps protect your computer by preventing unauthorized users from gaining access to your computer through the Internet or a network.",
                    "caption": "Windows Firewall"
                },
                {
                    "name": "MSDTC",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Distributed Transaction Coordinator",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\msdtc.exe",
                    "description": "Coordinates transactions that span multiple resource managers, such as databases, message queues, and file systems. If this service is stopped, these transactions will fail. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Distributed Transaction Coordinator"
                },
                {
                    "name": "MSiSCSI",
                    "start_name": "LocalSystem",
                    "display_name": "Microsoft iSCSI Initiator Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Manages Internet SCSI (iSCSI) sessions from this computer to remote iSCSI target devices. If this service is stopped, this computer will not be able to login or access iSCSI targets. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Microsoft iSCSI Initiator Service"
                },
                {
                    "name": "msiserver",
                    "start_name": "LocalSystem",
                    "display_name": "Windows Installer",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\msiexec.exe /V",
                    "description": "Adds, modifies, and removes applications provided as a Windows Installer (*.msi, *.msp) package. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Windows Installer"
                },
                {
                    "name": "NcaSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Network Connectivity Assistant",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k NetSvcs",
                    "description": "Provides DirectAccess status notification for UI components",
                    "caption": "Network Connectivity Assistant"
                },
                {
                    "name": "NcbService",
                    "start_name": "LocalSystem",
                    "display_name": "Network Connection Broker",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Brokers connections that allow Windows Store Apps to receive notifications from the internet.",
                    "caption": "Network Connection Broker"
                },
                {
                    "name": "Netlogon",
                    "start_name": "LocalSystem",
                    "display_name": "Netlogon",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\lsass.exe",
                    "description": "Maintains a secure channel between this computer and the domain controller for authenticating users and services. If this service is stopped, the computer may not authenticate users and services and the domain controller cannot register DNS records. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Netlogon"
                },
                {
                    "name": "Netman",
                    "start_name": "LocalSystem",
                    "display_name": "Network Connections",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Manages objects in the Network and Dial-Up Connections folder, in which you can view both local area network and remote connections.",
                    "caption": "Network Connections"
                },
                {
                    "name": "netprofm",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Network List Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalService",
                    "description": "Identifies the networks to which the computer has connected, collects and stores properties for these networks, and notifies applications when these properties change.",
                    "caption": "Network List Service"
                },
                {
                    "name": "NetSetupSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Network Setup Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "The Network Setup Service manages the installation of network drivers and permits the configuration of low-level network settings.  If this service is stopped, any driver installations that are in-progress may be cancelled.",
                    "caption": "Network Setup Service"
                },
                {
                    "name": "NetTcpPortSharing",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Net.Tcp Port Sharing Service",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\SMSvcHost.exe",
                    "description": "Provides ability to share TCP ports over the net.tcp protocol.",
                    "caption": "Net.Tcp Port Sharing Service"
                },
                {
                    "name": "NgcCtnrSvc",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Microsoft Passport Container",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Manages local user identity keys used to authenticate user to identity providers as well as TPM virtual smart cards. If this service is disabled, local user identity keys and TPM virtual smart cards will not be accessible. It is recommended that you do not reconfigure this service.",
                    "caption": "Microsoft Passport Container"
                },
                {
                    "name": "NgcSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Microsoft Passport",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Provides process isolation for cryptographic keys used to authenticate to a user’s associated identity providers. If this service is disabled, all uses and management of these keys will not be available, which includes machine logon and single-sign on for apps and websites. This service starts and stops automatically. It is recommended that you do not reconfigure this service.",
                    "caption": "Microsoft Passport"
                },
                {
                    "name": "NlaSvc",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Network Location Awareness",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k NetworkService",
                    "description": "Collects and stores configuration information for the network and notifies programs when this information is modified. If this service is stopped, configuration information might be unavailable. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Network Location Awareness"
                },
                {
                    "name": "nsi",
                    "start_name": "NT Authority\\LocalService",
                    "display_name": "Network Store Interface Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "This service delivers network notifications (e.g. interface addition/deleting etc) to user mode clients. Stopping this service will cause loss of network connectivity. If this service is disabled, any other services that explicitly depend on this service will fail to start.",
                    "caption": "Network Store Interface Service"
                },
                {
                    "name": "NTDS",
                    "start_name": "LocalSystem",
                    "display_name": "Active Directory Domain Services",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\lsass.exe",
                    "description": "AD DS Domain Controller service. If this service is stopped, users will be unable to log on to the network. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Active Directory Domain Services"
                },
                {
                    "name": "NtFrs",
                    "start_name": "LocalSystem",
                    "display_name": "File Replication",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\ntfrs.exe",
                    "description": "Synchronizes folders with file servers that use File Replication Service (FRS) instead of the newer DFS Replication technology.",
                    "caption": "File Replication"
                },
                {
                    "name": "PcaSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Program Compatibility Assistant Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "This service provides support for the Program Compatibility Assistant (PCA).  PCA monitors programs installed and run by the user and detects known compatibility problems. If this service is stopped, PCA will not function properly.",
                    "caption": "Program Compatibility Assistant Service"
                },
                {
                    "name": "PerfHost",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Performance Counter DLL Host",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\SysWow64\\perfhost.exe",
                    "description": "Enables remote users and 64-bit processes to query performance counters provided by 32-bit DLLs. If this service is stopped, only local users and 32-bit processes will be able to query performance counters provided by 32-bit DLLs.",
                    "caption": "Performance Counter DLL Host"
                },
                {
                    "name": "PhoneSvc",
                    "start_name": "NT Authority\\LocalService",
                    "display_name": "Phone Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "Manages the telephony state on the device",
                    "caption": "Phone Service"
                },
                {
                    "name": "pla",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Performance Logs & Alerts",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalServiceNoNetwork",
                    "description": "Performance Logs and Alerts Collects performance data from local or remote computers based on preconfigured schedule parameters, then writes the data to a log or triggers an alert. If this service is stopped, performance information will not be collected. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Performance Logs & Alerts"
                },
                {
                    "name": "PlugPlay",
                    "start_name": "LocalSystem",
                    "display_name": "Plug and Play",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k DcomLaunch",
                    "description": "Enables a computer to recognize and adapt to hardware changes with little or no user input. Stopping or disabling this service will result in system instability.",
                    "caption": "Plug and Play"
                },
                {
                    "name": "PolicyAgent",
                    "start_name": "NT Authority\\NetworkService",
                    "display_name": "IPsec Policy Agent",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k NetworkServiceNetworkRestricted",
                    "description": "Internet Protocol security (IPsec) supports network-level peer authentication, data origin authentication, data integrity, data confidentiality (encryption), and replay protection.  This service enforces IPsec policies created through the IP Security Policies snap-in or the command-line tool \"netsh ipsec\".  If you stop this service, you may experience network connectivity issues if your policy requires that connections use IPsec.  Also,remote management of Windows Firewall is not available when this service is stopped.",
                    "caption": "IPsec Policy Agent"
                },
                {
                    "name": "Power",
                    "start_name": "LocalSystem",
                    "display_name": "Power",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k DcomLaunch",
                    "description": "Manages power policy and power policy notification delivery.",
                    "caption": "Power"
                },
                {
                    "name": "PrintNotify",
                    "start_name": "LocalSystem",
                    "display_name": "Printer Extensions and Notifications",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k print",
                    "description": "This service opens custom printer dialog boxes and handles notifications from a remote print server or a printer. If you turn off this service, you won’t be able to see printer extensions or notifications.",
                    "caption": "Printer Extensions and Notifications"
                },
                {
                    "name": "ProfSvc",
                    "start_name": "LocalSystem",
                    "display_name": "User Profile Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "This service is responsible for loading and unloading user profiles. If this service is stopped or disabled, users will no longer be able to successfully sign in or sign out, apps might have problems getting to users' data, and components registered to receive profile event notifications won't receive them.",
                    "caption": "User Profile Service"
                },
                {
                    "name": "QWAVE",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Quality Windows Audio Video Experience",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceAndNoImpersonation",
                    "description": "Quality Windows Audio Video Experience (qWave) is a networking platform for Audio Video (AV) streaming applications on IP home networks. qWave enhances AV streaming performance and reliability by ensuring network quality-of-service (QoS) for AV applications. It provides mechanisms for admission control, run time monitoring and enforcement, application feedback, and traffic prioritization.",
                    "caption": "Quality Windows Audio Video Experience"
                },
                {
                    "name": "RasAuto",
                    "start_name": "localSystem",
                    "display_name": "Remote Access Auto Connection Manager",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "Creates a connection to a remote network whenever a program references a remote DNS or NetBIOS name or address.",
                    "caption": "Remote Access Auto Connection Manager"
                },
                {
                    "name": "RasMan",
                    "start_name": "localSystem",
                    "display_name": "Remote Access Connection Manager",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "Manages dial-up and virtual private network (VPN) connections from this computer to the Internet or other remote networks. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Remote Access Connection Manager"
                },
                {
                    "name": "RemoteAccess",
                    "start_name": "localSystem",
                    "display_name": "Routing and Remote Access",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "Offers routing services to businesses in local area and wide area network environments.",
                    "caption": "Routing and Remote Access"
                },
                {
                    "name": "RemoteRegistry",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Remote Registry",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k localService",
                    "description": "Enables remote users to modify registry settings on this computer. If this service is stopped, the registry can be modified only by users on this computer. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Remote Registry"
                },
                {
                    "name": "RmSvc",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Radio Management Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Radio Management and Airplane Mode Service",
                    "caption": "Radio Management Service"
                },
                {
                    "name": "RpcEptMapper",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "RPC Endpoint Mapper",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k RPCSS",
                    "description": "Resolves RPC interfaces identifiers to transport endpoints. If this service is stopped or disabled, programs using Remote Procedure Call (RPC) services will not function properly.",
                    "caption": "RPC Endpoint Mapper"
                },
                {
                    "name": "RpcLocator",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Remote Procedure Call (RPC) Locator",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\locator.exe",
                    "description": "In Windows 2003 and earlier versions of Windows, the Remote Procedure Call (RPC) Locator service manages the RPC name service database. In Windows Vista and later versions of Windows, this service does not provide any functionality and is present for application compatibility.",
                    "caption": "Remote Procedure Call (RPC) Locator"
                },
                {
                    "name": "RpcSs",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Remote Procedure Call (RPC)",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k rpcss",
                    "description": "The RPCSS service is the Service Control Manager for COM and DCOM servers. It performs object activations requests, object exporter resolutions and distributed garbage collection for COM and DCOM servers. If this service is stopped or disabled, programs using COM or DCOM will not function properly. It is strongly recommended that you have the RPCSS service running.",
                    "caption": "Remote Procedure Call (RPC)"
                },
                {
                    "name": "RSoPProv",
                    "start_name": "LocalSystem",
                    "display_name": "Resultant Set of Policy Provider",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\RSoPProv.exe",
                    "description": "Provides a network service that processes requests to simulate application of Group Policy settings for a target user or computer in various situations and computes the Resultant Set of Policy settings.",
                    "caption": "Resultant Set of Policy Provider"
                },
                {
                    "name": "sacsvr",
                    "start_name": "LocalSystem",
                    "display_name": "Special Administration Console Helper",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "Allows administrators to remotely access a command prompt using Emergency Management Services.",
                    "caption": "Special Administration Console Helper"
                },
                {
                    "name": "SamSs",
                    "start_name": "LocalSystem",
                    "display_name": "Security Accounts Manager",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\lsass.exe",
                    "description": "The startup of this service signals other services that the Security Accounts Manager (SAM) is ready to accept requests.  Disabling this service will prevent other services in the system from being notified when the SAM is ready, which may in turn cause those services to fail to start correctly. This service should not be disabled.",
                    "caption": "Security Accounts Manager"
                },
                {
                    "name": "SCardSvr",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Smart Card",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceAndNoImpersonation",
                    "description": "Manages access to smart cards read by this computer. If this service is stopped, this computer will be unable to read smart cards. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Smart Card"
                },
                {
                    "name": "ScDeviceEnum",
                    "start_name": "LocalSystem",
                    "display_name": "Smart Card Device Enumeration Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Creates software device nodes for all smart card readers accessible to a given session. If this service is disabled, WinRT APIs will not be able to enumerate smart card readers.",
                    "caption": "Smart Card Device Enumeration Service"
                },
                {
                    "name": "Schedule",
                    "start_name": "LocalSystem",
                    "display_name": "Task Scheduler",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Enables a user to configure and schedule automated tasks on this computer. The service also hosts multiple Windows system-critical tasks. If this service is stopped or disabled, these tasks will not be run at their scheduled times. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Task Scheduler"
                },
                {
                    "name": "SCPolicySvc",
                    "start_name": "LocalSystem",
                    "display_name": "Smart Card Removal Policy",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Allows the system to be configured to lock the user desktop upon smart card removal.",
                    "caption": "Smart Card Removal Policy"
                },
                {
                    "name": "seclogon",
                    "start_name": "LocalSystem",
                    "display_name": "Secondary Logon",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Enables starting processes under alternate credentials. If this service is stopped, this type of logon access will be unavailable. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Secondary Logon"
                },
                {
                    "name": "SENS",
                    "start_name": "LocalSystem",
                    "display_name": "System Event Notification Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Monitors system events and notifies subscribers to COM+ Event System of these events.",
                    "caption": "System Event Notification Service"
                },
                {
                    "name": "SensorDataService",
                    "start_name": "LocalSystem",
                    "display_name": "Sensor Data Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\SensorDataService.exe",
                    "description": "Delivers data from a variety of sensors",
                    "caption": "Sensor Data Service"
                },
                {
                    "name": "SensorService",
                    "start_name": "LocalSystem",
                    "display_name": "Sensor Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "A service for sensors that manages different sensors' functionality. Manages Simple Device Orientation (SDO) and History for sensors. Loads the SDO sensor that reports device orientation changes.  If this service is stopped or disabled, the SDO sensor will not be loaded and so auto-rotation will not occur. History collection from Sensors will also be stopped.",
                    "caption": "Sensor Service"
                },
                {
                    "name": "SensrSvc",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Sensor Monitoring Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceAndNoImpersonation",
                    "description": "Monitors various sensors in order to expose data and adapt to system and user state.  If this service is stopped or disabled, the display brightness will not adapt to lighting conditions. Stopping this service may affect other system functionality and features as well.",
                    "caption": "Sensor Monitoring Service"
                },
                {
                    "name": "SessionEnv",
                    "start_name": "localSystem",
                    "display_name": "Remote Desktop Configuration",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "Remote Desktop Configuration service (RDCS) is responsible for all Remote Desktop Services and Remote Desktop related configuration and session maintenance activities that require SYSTEM context. These include per-session temporary folders, RD themes, and RD certificates.",
                    "caption": "Remote Desktop Configuration"
                },
                {
                    "name": "SharedAccess",
                    "start_name": "LocalSystem",
                    "display_name": "Internet Connection Sharing (ICS)",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "Provides network address translation, addressing, name resolution and/or intrusion prevention services for a home or small office network.",
                    "caption": "Internet Connection Sharing (ICS)"
                },
                {
                    "name": "ShellHWDetection",
                    "start_name": "LocalSystem",
                    "display_name": "Shell Hardware Detection",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "Provides notifications for AutoPlay hardware events.",
                    "caption": "Shell Hardware Detection"
                },
                {
                    "name": "smphost",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Microsoft Storage Spaces SMP",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k smphost",
                    "description": "Host service for the Microsoft Storage Spaces management provider. If this service is stopped or disabled, Storage Spaces cannot be managed.",
                    "caption": "Microsoft Storage Spaces SMP"
                },
                {
                    "name": "SNMPTRAP",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "SNMP Trap",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\snmptrap.exe",
                    "description": "Receives trap messages generated by local or remote Simple Network Management Protocol (SNMP) agents and forwards the messages to SNMP management programs running on this computer. If this service is stopped, SNMP-based programs on this computer will not receive SNMP trap messages. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "SNMP Trap"
                },
                {
                    "name": "Spooler",
                    "start_name": "LocalSystem",
                    "display_name": "Print Spooler",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\spoolsv.exe",
                    "description": "This service spools print jobs and handles interaction with the printer.  If you turn off this service, you won’t be able to print or see your printers.",
                    "caption": "Print Spooler"
                },
                {
                    "name": "sppsvc",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Software Protection",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\sppsvc.exe",
                    "description": "Enables the download, installation and enforcement of digital licenses for Windows and Windows applications. If the service is disabled, the operating system and licensed applications may run in a notification mode. It is strongly recommended that you not disable the Software Protection service.",
                    "caption": "Software Protection"
                },
                {
                    "name": "SSDPSRV",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "SSDP Discovery",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceAndNoImpersonation",
                    "description": "Discovers networked devices and services that use the SSDP discovery protocol, such as UPnP devices. Also announces SSDP devices and services running on the local computer. If this service is stopped, SSDP-based devices will not be discovered. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "SSDP Discovery"
                },
                {
                    "name": "SstpSvc",
                    "start_name": "NT Authority\\LocalService",
                    "display_name": "Secure Socket Tunneling Protocol Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "Provides support for the Secure Socket Tunneling Protocol (SSTP) to connect to remote computers using VPN. If this service is disabled, users will not be able to use SSTP to access remote servers.",
                    "caption": "Secure Socket Tunneling Protocol Service"
                },
                {
                    "name": "StateRepository",
                    "start_name": "LocalSystem",
                    "display_name": "State Repository Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k appmodel",
                    "description": "Provides required infrastructure support for the application model.",
                    "caption": "State Repository Service"
                },
                {
                    "name": "stisvc",
                    "start_name": "NT Authority\\LocalService",
                    "display_name": "Windows Image Acquisition (WIA)",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k imgsvc",
                    "description": "Provides image acquisition services for scanners and cameras",
                    "caption": "Windows Image Acquisition (WIA)"
                },
                {
                    "name": "StorSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Storage Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Provides enabling services for storage settings and external storage expansion",
                    "caption": "Storage Service"
                },
                {
                    "name": "svsvc",
                    "start_name": "LocalSystem",
                    "display_name": "Spot Verifier",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Verifies potential file system corruptions.",
                    "caption": "Spot Verifier"
                },
                {
                    "name": "swprv",
                    "start_name": "LocalSystem",
                    "display_name": "Microsoft Software Shadow Copy Provider",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k swprv",
                    "description": "Manages software-based volume shadow copies taken by the Volume Shadow Copy service. If this service is stopped, software-based volume shadow copies cannot be managed. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Microsoft Software Shadow Copy Provider"
                },
                {
                    "name": "SysMain",
                    "start_name": "LocalSystem",
                    "display_name": "Superfetch",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Maintains and improves system performance over time.",
                    "caption": "Superfetch"
                },
                {
                    "name": "SystemEventsBroker",
                    "start_name": "LocalSystem",
                    "display_name": "System Events Broker",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k DcomLaunch",
                    "description": "Coordinates execution of background work for WinRT application. If this service is stopped or disabled, then background work might not be triggered.",
                    "caption": "System Events Broker"
                },
                {
                    "name": "TabletInputService",
                    "start_name": "LocalSystem",
                    "display_name": "Touch Keyboard and Handwriting Panel Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Enables Touch Keyboard and Handwriting Panel pen and ink functionality",
                    "caption": "Touch Keyboard and Handwriting Panel Service"
                },
                {
                    "name": "TapiSrv",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Telephony",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k NetworkService",
                    "description": "Provides Telephony API (TAPI) support for programs that control telephony devices on the local computer and, through the LAN, on servers that are also running the service.",
                    "caption": "Telephony"
                },
                {
                    "name": "TermService",
                    "start_name": "NT Authority\\NetworkService",
                    "display_name": "Remote Desktop Services",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k termsvcs",
                    "description": "Allows users to connect interactively to a remote computer. Remote Desktop and Remote Desktop Session Host Server depend on this service.  To prevent remote use of this computer, clear the checkboxes on the Remote tab of the System properties control panel item.",
                    "caption": "Remote Desktop Services"
                },
                {
                    "name": "Themes",
                    "start_name": "LocalSystem",
                    "display_name": "Themes",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "Provides user experience theme management.",
                    "caption": "Themes"
                },
                {
                    "name": "TieringEngineService",
                    "start_name": "localSystem",
                    "display_name": "Storage Tiers Management",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\TieringEngineService.exe",
                    "description": "Optimizes the placement of data in storage tiers on all tiered storage spaces in the system.",
                    "caption": "Storage Tiers Management"
                },
                {
                    "name": "tiledatamodelsvc",
                    "start_name": "LocalSystem",
                    "display_name": "Tile Data model server",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k appmodel",
                    "description": "Tile Server for tile updates.",
                    "caption": "Tile Data model server"
                },
                {
                    "name": "TimeBrokerSvc",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Time Broker",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Coordinates execution of background work for WinRT application. If this service is stopped or disabled, then background work might not be triggered.",
                    "caption": "Time Broker"
                },
                {
                    "name": "TrkWks",
                    "start_name": "LocalSystem",
                    "display_name": "Distributed Link Tracking Client",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Maintains links between NTFS files within a computer or across computers in a network.",
                    "caption": "Distributed Link Tracking Client"
                },
                {
                    "name": "TrustedInstaller",
                    "start_name": "localSystem",
                    "display_name": "Windows Modules Installer",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\servicing\\TrustedInstaller.exe",
                    "description": "Enables installation, modification, and removal of Windows updates and optional components. If this service is disabled, install or uninstall of Windows updates might fail for this computer.",
                    "caption": "Windows Modules Installer"
                },
                {
                    "name": "tzautoupdate",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Auto Time Zone Updater",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "Automatically sets the system time zone.",
                    "caption": "Auto Time Zone Updater"
                },
                {
                    "name": "UALSVC",
                    "start_name": "LocalSystem",
                    "display_name": "User Access Logging Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "This service logs unique client access requests, in the form of IP addresses and user names, of installed products and roles on the local server. This information can be queried, via Powershell, by administrators needing to quantify client demand of server software for offline Client Access License (CAL) management. If the service is disabled, client requests will not be logged and will not be retrievable via Powershell queries. Stopping the service will not affect query of historical data (see supporting documentation for steps to delete historical data). The local system administrator must consult his, or her, Windows Server license terms to determine the number of CALs that are required for the server software to be appropriately licensed; use of the UAL service and data does not alter this obligation.",
                    "caption": "User Access Logging Service"
                },
                {
                    "name": "UevAgentService",
                    "start_name": "LocalSystem",
                    "display_name": "User Experience Virtualization Service",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\AgentService.exe",
                    "description": "Provides support for application and OS settings roaming",
                    "caption": "User Experience Virtualization Service"
                },
                {
                    "name": "UI0Detect",
                    "start_name": "LocalSystem",
                    "display_name": "Interactive Services Detection",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\UI0Detect.exe",
                    "description": "Enables user notification of user input for interactive services, which enables access to dialogs created by interactive services when they appear. If this service is stopped, notifications of new interactive service dialogs will no longer function and there might not be access to interactive service dialogs. If this service is disabled, both notifications of and access to new interactive service dialogs will no longer function.",
                    "caption": "Interactive Services Detection"
                },
                {
                    "name": "UmRdpService",
                    "start_name": "localSystem",
                    "display_name": "Remote Desktop Services UserMode Port Redirector",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Allows the redirection of Printers/Drives/Ports for RDP connections",
                    "caption": "Remote Desktop Services UserMode Port Redirector"
                },
                {
                    "name": "upnphost",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "UPnP Device Host",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceAndNoImpersonation",
                    "description": "Allows UPnP devices to be hosted on this computer. If this service is stopped, any hosted UPnP devices will stop functioning and no additional hosted devices can be added. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "UPnP Device Host"
                },
                {
                    "name": "UserManager",
                    "start_name": "LocalSystem",
                    "display_name": "User Manager",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "User Manager provides the runtime components required for multi-user interaction.  If this service is stopped, some applications may not operate correctly.",
                    "caption": "User Manager"
                },
                {
                    "name": "UsoSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Update Orchestrator Service for Windows Update",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "UsoSvc",
                    "caption": "Update Orchestrator Service for Windows Update"
                },
                {
                    "name": "VaultSvc",
                    "start_name": "LocalSystem",
                    "display_name": "Credential Manager",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\lsass.exe",
                    "description": "Provides secure storage and retrieval of credentials to users, applications and security service packages.",
                    "caption": "Credential Manager"
                },
                {
                    "name": "vds",
                    "start_name": "LocalSystem",
                    "display_name": "Virtual Disk",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\vds.exe",
                    "description": "Provides management services for disks, volumes, file systems, and storage arrays.",
                    "caption": "Virtual Disk"
                },
                {
                    "name": "vmicguestinterface",
                    "start_name": "LocalSystem",
                    "display_name": "Hyper-V Guest Service Interface",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Provides an interface for the Hyper-V host to interact with specific services running inside the virtual machine.",
                    "caption": "Hyper-V Guest Service Interface"
                },
                {
                    "name": "vmicheartbeat",
                    "start_name": "LocalSystem",
                    "display_name": "Hyper-V Heartbeat Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k ICService",
                    "description": "Monitors the state of this virtual machine by reporting a heartbeat at regular intervals. This service helps you identify running virtual machines that have stopped responding.",
                    "caption": "Hyper-V Heartbeat Service"
                },
                {
                    "name": "vmickvpexchange",
                    "start_name": "LocalSystem",
                    "display_name": "Hyper-V Data Exchange Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Provides a mechanism to exchange data between the virtual machine and the operating system running on the physical computer.",
                    "caption": "Hyper-V Data Exchange Service"
                },
                {
                    "name": "vmicrdv",
                    "start_name": "LocalSystem",
                    "display_name": "Hyper-V Remote Desktop Virtualization Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k ICService",
                    "description": "Provides a platform for communication between the virtual machine and the operating system running on the physical computer.",
                    "caption": "Hyper-V Remote Desktop Virtualization Service"
                },
                {
                    "name": "vmicshutdown",
                    "start_name": "LocalSystem",
                    "display_name": "Hyper-V Guest Shutdown Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Provides a mechanism to shut down the operating system of this virtual machine from the management interfaces on the physical computer.",
                    "caption": "Hyper-V Guest Shutdown Service"
                },
                {
                    "name": "vmictimesync",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Hyper-V Time Synchronization Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Synchronizes the system time of this virtual machine with the system time of the physical computer.",
                    "caption": "Hyper-V Time Synchronization Service"
                },
                {
                    "name": "vmicvmsession",
                    "start_name": "LocalSystem",
                    "display_name": "Hyper-V PowerShell Direct Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Provides a mechanism to manage virtual machine with PowerShell via VM session without a virtual network.",
                    "caption": "Hyper-V PowerShell Direct Service"
                },
                {
                    "name": "vmicvss",
                    "start_name": "LocalSystem",
                    "display_name": "Hyper-V Volume Shadow Copy Requestor",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Coordinates the communications that are required to use Volume Shadow Copy Service to back up applications and data on this virtual machine from the operating system on the physical computer.",
                    "caption": "Hyper-V Volume Shadow Copy Requestor"
                },
                {
                    "name": "VSS",
                    "start_name": "LocalSystem",
                    "display_name": "Volume Shadow Copy",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\vssvc.exe",
                    "description": "Manages and implements Volume Shadow Copies used for backup and other purposes. If this service is stopped, shadow copies will be unavailable for backup and the backup may fail. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Volume Shadow Copy"
                },
                {
                    "name": "w32time",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Windows Time",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "Maintains date and time synchronization on all clients and servers in the network. If this service is stopped, date and time synchronization will be unavailable. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Windows Time"
                },
                {
                    "name": "WalletService",
                    "start_name": "LocalSystem",
                    "display_name": "WalletService",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k appmodel",
                    "description": "Hosts objects used by clients of the wallet",
                    "caption": "WalletService"
                },
                {
                    "name": "WbioSrvc",
                    "start_name": "LocalSystem",
                    "display_name": "Windows Biometric Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k WbioSvcGroup",
                    "description": "The Windows biometric service gives client applications the ability to capture, compare, manipulate, and store biometric data without gaining direct access to any biometric hardware or samples. The service is hosted in a privileged SVCHOST process.",
                    "caption": "Windows Biometric Service"
                },
                {
                    "name": "Wcmsvc",
                    "start_name": "NT Authority\\LocalService",
                    "display_name": "Windows Connection Manager",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalServiceNetworkRestricted",
                    "description": "Makes automatic connect/disconnect decisions based on the network connectivity options currently available to the PC and enables management of network connectivity based on Group Policy settings.",
                    "caption": "Windows Connection Manager"
                },
                {
                    "name": "WdiServiceHost",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Diagnostic Service Host",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalService",
                    "description": "The Diagnostic Service Host is used by the Diagnostic Policy Service to host diagnostics that need to run in a Local Service context.  If this service is stopped, any diagnostics that depend on it will no longer function.",
                    "caption": "Diagnostic Service Host"
                },
                {
                    "name": "WdiSystemHost",
                    "start_name": "LocalSystem",
                    "display_name": "Diagnostic System Host",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "The Diagnostic System Host is used by the Diagnostic Policy Service to host diagnostics that need to run in a Local System context.  If this service is stopped, any diagnostics that depend on it will no longer function.",
                    "caption": "Diagnostic System Host"
                },
                {
                    "name": "WdNisSvc",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Windows Defender Network Inspection Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "\"C:\\ProgramData\\Microsoft\\Windows Defender\\platform\\4.18.2005.5-0\\NisSrv.exe\"",
                    "description": "Helps guard against intrusion attempts targeting known and newly discovered vulnerabilities in network protocols",
                    "caption": "Windows Defender Network Inspection Service"
                },
                {
                    "name": "Wecsvc",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Windows Event Collector",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k NetworkService",
                    "description": "This service manages persistent subscriptions to events from remote sources that support WS-Management protocol. This includes Windows Vista event logs, hardware and IPMI-enabled event sources. The service stores forwarded events in a local Event Log. If this service is stopped or disabled event subscriptions cannot be created and forwarded events cannot be accepted.",
                    "caption": "Windows Event Collector"
                },
                {
                    "name": "WEPHOSTSVC",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "Windows Encryption Provider Host Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k WepHostSvcGroup",
                    "description": "Windows Encryption Provider Host Service brokers encryption related functionalities from 3rd Party Encryption Providers to processes that need to evaluate and apply EAS policies. Stopping this will compromise EAS compliancy checks that have been established by the connected Mail Accounts",
                    "caption": "Windows Encryption Provider Host Service"
                },
                {
                    "name": "wercplsupport",
                    "start_name": "localSystem",
                    "display_name": "Problem Reports and Solutions Control Panel Support",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k netsvcs",
                    "description": "This service provides support for viewing, sending and deletion of system-level problem reports for the Problem Reports and Solutions control panel.",
                    "caption": "Problem Reports and Solutions Control Panel Support"
                },
                {
                    "name": "WerSvc",
                    "start_name": "localSystem",
                    "display_name": "Windows Error Reporting Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k WerSvcGroup",
                    "description": "Allows errors to be reported when programs stop working or responding and allows existing solutions to be delivered. Also allows logs to be generated for diagnostic and repair services. If this service is stopped, error reporting might not work correctly and results of diagnostic services and repairs might not be displayed.",
                    "caption": "Windows Error Reporting Service"
                },
                {
                    "name": "WiaRpc",
                    "start_name": "LocalSystem",
                    "display_name": "Still Image Acquisition Events",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Launches applications associated with still image acquisition events.",
                    "caption": "Still Image Acquisition Events"
                },
                {
                    "name": "WinDefend",
                    "start_name": "LocalSystem",
                    "display_name": "Windows Defender Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Own Process",
                    "path_name": "\"C:\\ProgramData\\Microsoft\\Windows Defender\\platform\\4.18.2005.5-0\\MsMpEng.exe\"",
                    "description": "Helps protect users from malware and other potentially unwanted software",
                    "caption": "Windows Defender Service"
                },
                {
                    "name": "WinHttpAutoProxySvc",
                    "start_name": "NT AUTHORITY\\LocalService",
                    "display_name": "WinHTTP Web Proxy Auto-Discovery Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalService",
                    "description": "WinHTTP implements the client HTTP stack and provides developers with a Win32 API and COM Automation component for sending HTTP requests and receiving responses. In addition, WinHTTP provides support for auto-discovering a proxy configuration via its implementation of the Web Proxy Auto-Discovery (WPAD) protocol.",
                    "caption": "WinHTTP Web Proxy Auto-Discovery Service"
                },
                {
                    "name": "Winmgmt",
                    "start_name": "localSystem",
                    "display_name": "Windows Management Instrumentation",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Provides a common interface and object model to access management information about operating system, devices, applications and services. If this service is stopped, most Windows-based software will not function properly. If this service is disabled, any services that explicitly depend on it will fail to start.",
                    "caption": "Windows Management Instrumentation"
                },
                {
                    "name": "WinRM",
                    "start_name": "NT AUTHORITY\\NetworkService",
                    "display_name": "Windows Remote Management (WS-Management)",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k NetworkService",
                    "description": "Windows Remote Management (WinRM) service implements the WS-Management protocol for remote management. WS-Management is a standard web services protocol used for remote software and hardware management. The WinRM service listens on the network for WS-Management requests and processes them. The WinRM Service needs to be configured with a listener using winrm.cmd command line tool or through Group Policy in order for it to listen over the network. The WinRM service provides access to WMI data and enables event collection. Event collection and subscription to events require that the service is running. WinRM messages use HTTP and HTTPS as transports. The WinRM service does not depend on IIS but is preconfigured to share a port with IIS on the same machine.  The WinRM service reserves the /wsman URL prefix. To prevent conflicts with IIS, administrators should ensure that any websites hosted on IIS do not use the /wsman URL prefix.",
                    "caption": "Windows Remote Management (WS-Management)"
                },
                {
                    "name": "wisvc",
                    "start_name": "LocalSystem",
                    "display_name": "Windows Insider Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "wisvc",
                    "caption": "Windows Insider Service"
                },
                {
                    "name": "wlidsvc",
                    "start_name": "LocalSystem",
                    "display_name": "Microsoft Account Sign-in Assistant",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Enables user sign-in through Microsoft account identity services. If this service is stopped, users will not be able to logon to the computer with their Microsoft account.",
                    "caption": "Microsoft Account Sign-in Assistant"
                },
                {
                    "name": "wmiApSrv",
                    "start_name": "localSystem",
                    "display_name": "WMI Performance Adapter",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\wbem\\WmiApSrv.exe",
                    "description": "Provides performance library information from Windows Management Instrumentation (WMI) providers to clients on the network. This service only runs when Performance Data Helper is activated.",
                    "caption": "WMI Performance Adapter"
                },
                {
                    "name": "WPDBusEnum",
                    "start_name": "LocalSystem",
                    "display_name": "Portable Device Enumerator Service",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Enforces group policy for removable mass-storage devices. Enables applications such as Windows Media Player and Image Import Wizard to transfer and synchronize content using removable mass-storage devices.",
                    "caption": "Portable Device Enumerator Service"
                },
                {
                    "name": "WpnService",
                    "start_name": "LocalSystem",
                    "display_name": "Windows Push Notifications System Service",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "This service runs in session 0 and hosts the notification platform and connection provider which handles the connection between the device and WNS server.",
                    "caption": "Windows Push Notifications System Service"
                },
                {
                    "name": "WSearch",
                    "start_name": "LocalSystem",
                    "display_name": "Windows Search",
                    "status": "OK",
                    "start_mode": "Disabled",
                    "service_type": "Own Process",
                    "path_name": "C:\\Windows\\system32\\SearchIndexer.exe /Embedding",
                    "description": "Provides content indexing, property caching, and search results for files, e-mail, and other content.",
                    "caption": "Windows Search"
                },
                {
                    "name": "wuauserv",
                    "start_name": "LocalSystem",
                    "display_name": "Windows Update",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Enables the detection, download, and installation of updates for Windows and other programs. If this service is disabled, users of this computer will not be able to use Windows Update or its automatic updating feature, and programs will not be able to use the Windows Update Agent (WUA) API.",
                    "caption": "Windows Update"
                },
                {
                    "name": "wudfsvc",
                    "start_name": "LocalSystem",
                    "display_name": "Windows Driver Foundation - User-mode Driver Framework",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k LocalSystemNetworkRestricted",
                    "description": "Creates and manages user-mode driver processes. This service cannot be stopped.",
                    "caption": "Windows Driver Foundation - User-mode Driver Framework"
                },
                {
                    "name": "XblAuthManager",
                    "start_name": "LocalSystem",
                    "display_name": "Xbox Live Auth Manager",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "Provides authentication and authorization services for interacting with Xbox Live. If this service is stopped, some applications may not operate correctly.",
                    "caption": "Xbox Live Auth Manager"
                },
                {
                    "name": "XblGameSave",
                    "start_name": "LocalSystem",
                    "display_name": "Xbox Live Game Save",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Share Process",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "description": "This service syncs save data for Xbox Live save enabled games.  If this service is stopped, game save data will not upload to or download from Xbox Live.",
                    "caption": "Xbox Live Game Save"
                },
                {
                    "name": "CDPUserSvc_41d6d",
                    "display_name": "CDPUserSvc_41d6d",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Unknown",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k UnistackSvcGroup",
                    "caption": "CDPUserSvc_41d6d"
                },
                {
                    "name": "OneSyncSvc_41d6d",
                    "display_name": "Sync Host_41d6d",
                    "status": "OK",
                    "start_mode": "Auto",
                    "service_type": "Unknown",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k UnistackSvcGroup",
                    "description": "This service synchronizes mail, contacts, calendar and various other user data. Mail and other applications dependent on this functionality will not work properly when this service is not running.",
                    "caption": "Sync Host_41d6d"
                },
                {
                    "name": "PimIndexMaintenanceSvc_41d6d",
                    "display_name": "Contact Data_41d6d",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Unknown",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k UnistackSvcGroup",
                    "description": "Indexes contact data for fast contact searching. If you stop or disable this service, contacts might be missing from your search results.",
                    "caption": "Contact Data_41d6d"
                },
                {
                    "name": "UnistoreSvc_41d6d",
                    "display_name": "User Data Storage_41d6d",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Unknown",
                    "path_name": "C:\\Windows\\System32\\svchost.exe -k UnistackSvcGroup",
                    "description": "Handles storage of structured user data, including contact info, calendars, messages, and other content. If you stop or disable this service, apps that use this data might not work correctly.",
                    "caption": "User Data Storage_41d6d"
                },
                {
                    "name": "UserDataSvc_41d6d",
                    "display_name": "User Data Access_41d6d",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Unknown",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k UnistackSvcGroup",
                    "description": "Provides apps access to structured user data, including contact info, calendars, messages, and other content. If you stop or disable this service, apps that use this data might not work correctly.",
                    "caption": "User Data Access_41d6d"
                },
                {
                    "name": "WpnUserService_41d6d",
                    "display_name": "Windows Push Notifications User Service_41d6d",
                    "status": "OK",
                    "start_mode": "Manual",
                    "service_type": "Unknown",
                    "path_name": "C:\\Windows\\system32\\svchost.exe -k UnistackSvcGroup",
                    "description": "This service hosts Windows notification platform which provides support for local and push notifications. Supported notifications are tile, toast and raw.",
                    "caption": "Windows Push Notifications User Service_41d6d"
                }
            ],
            "shares": [
                {
                    "name": "ADMIN$",
                    "description": "Remote Admin",
                    "path": "C:\\Windows"
                },
                {
                    "name": "C$",
                    "description": "Default share",
                    "path": "C:\\"
                },
                {
                    "name": "IPC$",
                    "description": "Remote IPC"
                },
                {
                    "name": "NETLOGON",
                    "description": "Logon server share ",
                    "path": "C:\\Windows\\SYSVOL\\sysvol\\TestDomain.test\\SCRIPTS"
                },
                {
                    "name": "SYSVOL",
                    "description": "Logon server share ",
                    "path": "C:\\Windows\\SYSVOL\\sysvol"
                }
            ],
            "ad_bad_config_no_lm_hash": 1,
            "ad_bad_config_force_guest": 0,
            "ad_bad_config_authentication_packages": [
                "msv1_0"
            ],
            "ad_bad_config_secure_boot": 1,
            "connected_hardware": [
                {
                    "hw_id": "PCI\\VEN_1AF4&DEV_1002&SUBSYS_00051AE0&REV_00\\3&13C0B0C5&0&28",
                    "name": "Google VirtIO Balloon Driver",
                    "manufacturer": "Google LLC."
                },
                {
                    "hw_id": "PCI\\VEN_1AF4&DEV_1000&SUBSYS_00011AF4&REV_00\\3&13C0B0C5&0&20",
                    "name": "Google VirtIO Ethernet Adapter",
                    "manufacturer": "Google LLC."
                },
                {
                    "hw_id": "ACPI\\PNP0F13\\4&1DBB554C&0",
                    "name": "PS/2 Compatible Mouse",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "SCSI\\DISK&VEN_GOOGLE&PROD_PERSISTENTDISK\\4&21CB0360&0&000100",
                    "name": "Google PersistentDisk SCSI Disk Device",
                    "manufacturer": "(Standard disk drives)"
                },
                {
                    "hw_id": "SWD\\PRINTENUM\\PRINTQUEUES",
                    "name": "Root Print Queue",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ROOT\\VOLMGR\\0000",
                    "name": "Volume Manager",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ACPI\\MSFT0101\\2&DABA3FF&1",
                    "name": "Trusted Platform Module 2.0",
                    "manufacturer": "(Standard)"
                },
                {
                    "hw_id": "ROOT\\BASICDISPLAY\\0000",
                    "name": "Microsoft Basic Display Driver",
                    "manufacturer": "(Standard display types)"
                },
                {
                    "hw_id": "SWD\\IP_TUNNEL_VBUS\\IP_TUNNEL_DEVICE_ROOT",
                    "name": "Microsoft IPv4 IPv6 Transition Adapter Bus",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ACPI\\PNP0B00\\4&1DBB554C&0",
                    "name": "System CMOS/real time clock",
                    "manufacturer": "(Standard system devices)"
                },
                {
                    "hw_id": "UMB\\UMB\\1&841921D&0&TERMINPUT_BUS",
                    "name": "UMBus Enumerator",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ACPI\\PNP0303\\4&1DBB554C&0",
                    "name": "Standard PS/2 Keyboard",
                    "manufacturer": "(Standard keyboards)"
                },
                {
                    "hw_id": "SWD\\PRINTENUM\\{678D5217-B3C9-4CAE-BA30-AE944CD954B0}",
                    "name": "Microsoft Print to PDF",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ROOT\\COMPOSITEBUS\\0000",
                    "name": "Composite Bus Enumerator",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ROOT\\VDRVROOT\\0000",
                    "name": "Microsoft Virtual Drive Enumerator",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "STORAGE\\VOLUME\\{A40284F0-A50D-11EA-B7F3-806E6F6E6963}#0000000000004400",
                    "name": "Volume",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "SWD\\IP_TUNNEL_VBUS\\ISATAP_0",
                    "name": "Microsoft ISATAP Adapter",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ROOT\\SPACEPORT\\0000",
                    "name": "Microsoft Storage Spaces Controller",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ACPI\\PNP0501\\1",
                    "name": "Communications Port (COM1)",
                    "manufacturer": "(Standard port types)"
                },
                {
                    "hw_id": "ACPI\\PNP0501\\3",
                    "name": "Communications Port (COM3)",
                    "manufacturer": "(Standard port types)"
                },
                {
                    "hw_id": "ACPI\\PNP0501\\4",
                    "name": "Communications Port (COM4)",
                    "manufacturer": "(Standard port types)"
                },
                {
                    "hw_id": "ROOT\\KDNIC\\0000",
                    "name": "Microsoft Kernel Debug Network Adapter",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "STORAGE\\VOLUME\\{A40284F0-A50D-11EA-B7F3-806E6F6E6963}#0000000001000000",
                    "name": "Volume",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ROOT\\UMBUS\\0000",
                    "name": "UMBus Root Bus Enumerator",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "SWD\\RADIO\\{3DB5895D-CC28-44B3-AD3D-6F01A782B8D2}",
                    "name": "Microsoft Radio Device Enumeration Bus",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "PCI\\VEN_8086&DEV_1237&SUBSYS_11001AF4&REV_02\\3&13C0B0C5&0&00",
                    "name": "CPU to PCI Bridge",
                    "manufacturer": "Intel"
                },
                {
                    "hw_id": "ROOT\\ACPI_HAL\\0000",
                    "name": "ACPI x64-based PC",
                    "manufacturer": "(Standard computers)"
                },
                {
                    "hw_id": "DISPLAY\\DEFAULT_MONITOR\\1&8713BCA&0&UID0",
                    "name": "Generic Non-PnP Monitor",
                    "manufacturer": "(Standard monitor types)"
                },
                {
                    "hw_id": "PCI\\VEN_8086&DEV_7110&SUBSYS_00000000&REV_03\\3&13C0B0C5&0&08",
                    "name": "PCI to ISA Bridge",
                    "manufacturer": "Intel"
                },
                {
                    "hw_id": "ACPI\\PNP0A03\\1",
                    "name": "PCI Bus",
                    "manufacturer": "(Standard system devices)"
                },
                {
                    "hw_id": "ACPI\\GENUINEINTEL_-_INTEL64_FAMILY_6_MODEL_63_-____________INTEL(R)_XEON(R)_CPU_@_2.30GHZ\\_0",
                    "name": "Intel(R) Xeon(R) CPU @ 2.30GHz",
                    "manufacturer": "Intel"
                },
                {
                    "hw_id": "ACPI\\GENUINEINTEL_-_INTEL64_FAMILY_6_MODEL_63_-____________INTEL(R)_XEON(R)_CPU_@_2.30GHZ\\_1",
                    "name": "Intel(R) Xeon(R) CPU @ 2.30GHz",
                    "manufacturer": "Intel"
                },
                {
                    "hw_id": "ACPI\\GENUINEINTEL_-_INTEL64_FAMILY_6_MODEL_63_-____________INTEL(R)_XEON(R)_CPU_@_2.30GHZ\\_2",
                    "name": "Intel(R) Xeon(R) CPU @ 2.30GHz",
                    "manufacturer": "Intel"
                },
                {
                    "hw_id": "ACPI\\GENUINEINTEL_-_INTEL64_FAMILY_6_MODEL_63_-____________INTEL(R)_XEON(R)_CPU_@_2.30GHZ\\_3",
                    "name": "Intel(R) Xeon(R) CPU @ 2.30GHz",
                    "manufacturer": "Intel"
                },
                {
                    "hw_id": "ACPI_HAL\\PNP0C08\\0",
                    "name": "Microsoft ACPI-Compliant System",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "HTREE\\ROOT\\0"
                },
                {
                    "hw_id": "ROOT\\BASICRENDER\\0000",
                    "name": "Microsoft Basic Render Driver",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ACPI\\FIXEDBUTTON\\2&DABA3FF&1",
                    "name": "ACPI Fixed Feature Button",
                    "manufacturer": "(Standard system devices)"
                },
                {
                    "hw_id": "PCI\\VEN_1AF4&DEV_1004&SUBSYS_00081AF4&REV_00\\3&13C0B0C5&0&18",
                    "name": "Google VirtIO SCSI pass-through controller",
                    "manufacturer": "Google LLC."
                },
                {
                    "hw_id": "STORAGE\\VOLUME\\{A40284F0-A50D-11EA-B7F3-806E6F6E6963}#0000000007400000",
                    "name": "Volume",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "SWD\\SCDEVICEENUMBUS\\0",
                    "name": "Smart Card Device Enumeration Bus",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "SWD\\SCDEVICEENUMBUS\\1",
                    "name": "Microsoft Passport Container Enumeration Bus",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ROOT\\NDISVIRTUALBUS\\0000",
                    "name": "NDIS Virtual Network Adapter Enumerator",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "SWD\\PRINTENUM\\{DCA65EED-57FF-48D9-8867-F27983A46FA5}",
                    "name": "Microsoft XPS Document Writer",
                    "manufacturer": "Microsoft"
                },
                {
                    "hw_id": "ACPI\\QEMU0001\\4&1DBB554C&0",
                    "name": "Google  PVPanic Device",
                    "manufacturer": "Google LLC."
                },
                {
                    "hw_id": "ROOT\\MSSMBIOS\\0000",
                    "name": "Microsoft System Management BIOS Driver",
                    "manufacturer": "(Standard system devices)"
                },
                {
                    "hw_id": "ROOT\\SYSTEM\\0000",
                    "name": "Plug and Play Software Device Enumerator",
                    "manufacturer": "(Standard system devices)"
                },
                {
                    "hw_id": "ROOT\\RDPBUS\\0000",
                    "name": "Remote Desktop Device Redirector Bus",
                    "manufacturer": "Microsoft"
                }
            ],
            "id": "device0",
            "connected_devices": [],
            "fetch_time": "2020-06-19 23:05:04",
            "adapter_properties": [
                "Assets"
            ],
            "first_fetch_time": "2020-06-19 22:36:00",
            "pretty_id": "AX-26"
        }
    ],
    "fields": [
        "adapters",
        "adapter_list_length",
        "internal_axon_id",
        "name",
        "hostname",
        "description",
        "last_seen",
        "fetch_time",
        "first_fetch_time",
        "network_interfaces",
        "network_interfaces.name",
        "network_interfaces.mac",
        "network_interfaces.manufacturer",
        "network_interfaces.ips",
        "network_interfaces.locations",
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
        "last_used_users",
        "installed_software",
        "installed_software.name",
        "installed_software.version",
        "installed_software.name_version",
        "installed_software.architecture",
        "installed_software.description",
        "installed_software.vendor",
        "installed_software.publisher",
        "installed_software.cve_count",
        "installed_software.sw_license",
        "installed_software.path",
        "installed_software.source",
        "software_cves",
        "software_cves.cve_id",
        "software_cves.software_name",
        "software_cves.software_version",
        "software_cves.software_vendor",
        "software_cves.cvss_version",
        "software_cves.cvss",
        "software_cves.cvss_str",
        "software_cves.cve_severity",
        "software_cves.cve_description",
        "software_cves.cve_synopsis",
        "software_cves.cve_references",
        "security_patches",
        "security_patches.security_patch_id",
        "security_patches.patch_description",
        "security_patches.classification",
        "security_patches.state",
        "security_patches.severity",
        "security_patches.bulletin_id",
        "connected_hardware",
        "connected_hardware.name",
        "connected_hardware.manufacturer",
        "connected_hardware.hw_id",
        "connected_devices",
        "connected_devices.remote_name",
        "connected_devices.local_ifaces",
        "connected_devices.local_ifaces.name",
        "connected_devices.local_ifaces.mac",
        "connected_devices.local_ifaces.manufacturer",
        "connected_devices.local_ifaces.ips",
        "connected_devices.local_ifaces.locations",
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
        "connected_devices.remote_ifaces.locations",
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
        "part_of_domain",
        "domain",
        "users",
        "users.user_sid",
        "users.username",
        "users.last_use_date",
        "users.is_local",
        "users.is_disabled",
        "users.is_admin",
        "users.user_department",
        "users.password_max_age",
        "users.interpreter",
        "local_admins",
        "local_admins.admin_name",
        "local_admins.admin_type",
        "local_admins_users",
        "local_admins_groups",
        "pc_type",
        "number_of_processes",
        "hard_drives",
        "hard_drives.path",
        "hard_drives.device",
        "hard_drives.file_system",
        "hard_drives.total_size",
        "hard_drives.free_size",
        "hard_drives.is_encrypted",
        "hard_drives.description",
        "hard_drives.serial_number",
        "cpus",
        "cpus.name",
        "cpus.manufacturer",
        "cpus.bitness",
        "cpus.family",
        "cpus.cores",
        "cpus.cores_thread",
        "cpus.load_percentage",
        "cpus.architecture",
        "cpus.ghz",
        "time_zone",
        "boot_time",
        "uptime",
        "device_manufacturer",
        "device_model",
        "device_serial",
        "bios_version",
        "bios_serial",
        "total_physical_memory",
        "free_physical_memory",
        "physical_memory_percentage",
        "total_number_of_physical_processors",
        "total_number_of_cores",
        "device_disabled",
        "device_managed_by",
        "organizational_unit",
        "processes",
        "processes.name",
        "services",
        "services.name",
        "services.display_name",
        "services.status",
        "services.start_name",
        "services.start_mode",
        "services.path_name",
        "services.description",
        "services.caption",
        "services.service_type",
        "shares",
        "shares.name",
        "shares.description",
        "shares.path",
        "shares.status",
        "adapter_properties",
        "labels",
        "hostname_preferred",
        "os.type_preferred",
        "os.distribution_preferred",
        "network_interfaces.mac_preferred",
        "network_interfaces.ips_preferred",
        "correlation_reasons"
    ],
    "additional_schema": [
        {
            "name": "ad_bad_config_no_lm_hash",
            "title": "Bad Config - No LMHash",
            "type": "integer"
        },
        {
            "name": "ad_bad_config_force_guest",
            "title": "Bad Config - Force Guest",
            "type": "integer"
        },
        {
            "items": {
                "type": "string"
            },
            "name": "ad_bad_config_authentication_packages",
            "title": "Bad Config - Authentication Packages",
            "type": "array"
        },
        {
            "name": "ad_bad_config_secure_boot",
            "title": "Bad Config - Secure Boot",
            "type": "integer"
        },
        {
            "name": "hostname",
            "title": "Host Name",
            "type": "string"
        },
        {
            "format": "date-time",
            "name": "fetch_time",
            "title": "Fetch Time",
            "type": "string"
        },
        {
            "format": "date-time",
            "name": "first_fetch_time",
            "title": "First Fetch Time",
            "type": "string"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Iface Name",
                        "type": "string"
                    },
                    {
                        "name": "mac",
                        "title": "MAC",
                        "type": "string"
                    },
                    {
                        "name": "manufacturer",
                        "title": "Manufacturer",
                        "type": "string"
                    },
                    {
                        "format": "ip",
                        "items": {
                            "format": "ip",
                            "type": "string"
                        },
                        "name": "ips",
                        "title": "IPs",
                        "type": "array"
                    },
                    {
                        "description": "Recognized Geo locations of the IPs",
                        "items": {
                            "type": "string"
                        },
                        "name": "locations",
                        "title": "Locations",
                        "type": "array"
                    },
                    {
                        "description": "A list of subnets in ip format, that correspond the IPs",
                        "format": "subnet",
                        "items": {
                            "format": "subnet",
                            "type": "string"
                        },
                        "name": "subnets",
                        "title": "Subnets",
                        "type": "array"
                    },
                    {
                        "description": "A list of vlans in this interface",
                        "items": {
                            "items": [
                                {
                                    "name": "name",
                                    "title": "Vlan Name",
                                    "type": "string"
                                },
                                {
                                    "name": "tagid",
                                    "title": "Tag ID",
                                    "type": "integer"
                                },
                                {
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ],
                                    "name": "tagness",
                                    "title": "Vlan Tagness",
                                    "type": "string"
                                }
                            ],
                            "type": "array"
                        },
                        "name": "vlan_list",
                        "title": "Vlans",
                        "type": "array"
                    },
                    {
                        "branched": true,
                        "name": "vlan_list.name",
                        "title": "Vlans: Vlan Name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "vlan_list.tagid",
                        "title": "Vlans: Tag ID",
                        "type": "integer"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ],
                        "name": "vlan_list.tagness",
                        "title": "Vlans: Vlan Tagness",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Up",
                            "Down",
                            "Testing",
                            "Unknown",
                            "Dormant",
                            "Nonpresent",
                            "LowerLayerDown"
                        ],
                        "name": "operational_status",
                        "title": "Operational Status",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Up",
                            "Down",
                            "Testing"
                        ],
                        "name": "admin_status",
                        "title": "Admin Status",
                        "type": "string"
                    },
                    {
                        "description": "Interface max speed per Second",
                        "name": "speed",
                        "title": "Interface Speed",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Access",
                            "Trunk"
                        ],
                        "name": "port_type",
                        "title": "Port Type",
                        "type": "string"
                    },
                    {
                        "description": "Interface Maximum transmission unit",
                        "name": "mtu",
                        "title": "MTU",
                        "type": "string"
                    },
                    {
                        "name": "gateway",
                        "title": "Gateway",
                        "type": "string"
                    },
                    {
                        "name": "port",
                        "title": "Port",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "network_interfaces",
            "title": "Network Interfaces",
            "type": "array"
        },
        {
            "branched": true,
            "name": "network_interfaces.name",
            "title": "Network Interfaces: Iface Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "network_interfaces.mac",
            "title": "Network Interfaces: MAC",
            "type": "string"
        },
        {
            "branched": true,
            "name": "network_interfaces.manufacturer",
            "title": "Network Interfaces: Manufacturer",
            "type": "string"
        },
        {
            "format": "ip",
            "items": {
                "format": "ip",
                "type": "string"
            },
            "name": "network_interfaces.ips",
            "title": "Network Interfaces: IPs",
            "type": "array"
        },
        {
            "description": "Recognized Geo locations of the IPs",
            "items": {
                "type": "string"
            },
            "name": "network_interfaces.locations",
            "title": "Network Interfaces: Locations",
            "type": "array"
        },
        {
            "description": "A list of subnets in ip format, that correspond the IPs",
            "format": "subnet",
            "items": {
                "format": "subnet",
                "type": "string"
            },
            "name": "network_interfaces.subnets",
            "title": "Network Interfaces: Subnets",
            "type": "array"
        },
        {
            "description": "A list of vlans in this interface",
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Vlan Name",
                        "type": "string"
                    },
                    {
                        "name": "tagid",
                        "title": "Tag ID",
                        "type": "integer"
                    },
                    {
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ],
                        "name": "tagness",
                        "title": "Vlan Tagness",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "network_interfaces.vlan_list",
            "title": "Network Interfaces: Vlans",
            "type": "array"
        },
        {
            "branched": true,
            "name": "network_interfaces.vlan_list.name",
            "title": "Network Interfaces: Vlans: Vlan Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "network_interfaces.vlan_list.tagid",
            "title": "Network Interfaces: Vlans: Tag ID",
            "type": "integer"
        },
        {
            "branched": true,
            "enum": [
                "Tagged",
                "Untagged"
            ],
            "name": "network_interfaces.vlan_list.tagness",
            "title": "Network Interfaces: Vlans: Vlan Tagness",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Up",
                "Down",
                "Testing",
                "Unknown",
                "Dormant",
                "Nonpresent",
                "LowerLayerDown"
            ],
            "name": "network_interfaces.operational_status",
            "title": "Network Interfaces: Operational Status",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Up",
                "Down",
                "Testing"
            ],
            "name": "network_interfaces.admin_status",
            "title": "Network Interfaces: Admin Status",
            "type": "string"
        },
        {
            "branched": true,
            "description": "Interface max speed per Second",
            "name": "network_interfaces.speed",
            "title": "Network Interfaces: Interface Speed",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Access",
                "Trunk"
            ],
            "name": "network_interfaces.port_type",
            "title": "Network Interfaces: Port Type",
            "type": "string"
        },
        {
            "branched": true,
            "description": "Interface Maximum transmission unit",
            "name": "network_interfaces.mtu",
            "title": "Network Interfaces: MTU",
            "type": "string"
        },
        {
            "branched": true,
            "name": "network_interfaces.gateway",
            "title": "Network Interfaces: Gateway",
            "type": "string"
        },
        {
            "branched": true,
            "name": "network_interfaces.port",
            "title": "Network Interfaces: Port",
            "type": "string"
        },
        {
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
            ],
            "name": "os.type",
            "title": "OS: Type",
            "type": "string"
        },
        {
            "name": "os.distribution",
            "title": "OS: Distribution",
            "type": "string"
        },
        {
            "name": "os.is_windows_server",
            "title": "OS: Is Windows Server",
            "type": "bool"
        },
        {
            "name": "os.os_str",
            "title": "OS: Full OS String",
            "type": "string"
        },
        {
            "enum": [
                32,
                64
            ],
            "name": "os.bitness",
            "title": "OS: Bitness",
            "type": "integer"
        },
        {
            "name": "os.sp",
            "title": "OS: Service Pack",
            "type": "string"
        },
        {
            "format": "date-time",
            "name": "os.install_date",
            "title": "OS: Install Date",
            "type": "string"
        },
        {
            "name": "os.kernel_version",
            "title": "OS: Kernel Version",
            "type": "string"
        },
        {
            "name": "os.codename",
            "title": "OS: Code name",
            "type": "string"
        },
        {
            "name": "os.major",
            "title": "OS: Major",
            "type": "integer"
        },
        {
            "name": "os.minor",
            "title": "OS: Minor",
            "type": "integer"
        },
        {
            "name": "os.build",
            "title": "OS: Build",
            "type": "string"
        },
        {
            "name": "os.serial",
            "title": "OS: Serial",
            "type": "string"
        },
        {
            "items": {
                "type": "string"
            },
            "name": "last_used_users",
            "title": "Last Used Users",
            "type": "array"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Software Name",
                        "type": "string"
                    },
                    {
                        "format": "version",
                        "name": "version",
                        "title": "Software Version",
                        "type": "string"
                    },
                    {
                        "name": "name_version",
                        "title": "Software Name and Version",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "x86",
                            "x64",
                            "MIPS",
                            "Alpha",
                            "PowerPC",
                            "ARM",
                            "ia64",
                            "all",
                            "i686"
                        ],
                        "name": "architecture",
                        "title": "Software Architecture",
                        "type": "string"
                    },
                    {
                        "name": "description",
                        "title": "Software Description",
                        "type": "string"
                    },
                    {
                        "name": "vendor",
                        "title": "Software Vendor",
                        "type": "string"
                    },
                    {
                        "name": "publisher",
                        "title": "Software Publisher",
                        "type": "string"
                    },
                    {
                        "name": "cve_count",
                        "title": "CVE Count",
                        "type": "string"
                    },
                    {
                        "name": "sw_license",
                        "title": "License",
                        "type": "string"
                    },
                    {
                        "name": "path",
                        "title": "Software Path",
                        "type": "string"
                    },
                    {
                        "name": "source",
                        "title": "Source",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "installed_software",
            "title": "Installed Software",
            "type": "array"
        },
        {
            "branched": true,
            "name": "installed_software.name",
            "title": "Installed Software: Software Name",
            "type": "string"
        },
        {
            "branched": true,
            "format": "version",
            "name": "installed_software.version",
            "title": "Installed Software: Software Version",
            "type": "string"
        },
        {
            "branched": true,
            "name": "installed_software.name_version",
            "title": "Installed Software: Software Name and Version",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "x86",
                "x64",
                "MIPS",
                "Alpha",
                "PowerPC",
                "ARM",
                "ia64",
                "all",
                "i686"
            ],
            "name": "installed_software.architecture",
            "title": "Installed Software: Software Architecture",
            "type": "string"
        },
        {
            "branched": true,
            "name": "installed_software.description",
            "title": "Installed Software: Software Description",
            "type": "string"
        },
        {
            "branched": true,
            "name": "installed_software.vendor",
            "title": "Installed Software: Software Vendor",
            "type": "string"
        },
        {
            "branched": true,
            "name": "installed_software.publisher",
            "title": "Installed Software: Software Publisher",
            "type": "string"
        },
        {
            "branched": true,
            "name": "installed_software.cve_count",
            "title": "Installed Software: CVE Count",
            "type": "string"
        },
        {
            "branched": true,
            "name": "installed_software.sw_license",
            "title": "Installed Software: License",
            "type": "string"
        },
        {
            "branched": true,
            "name": "installed_software.path",
            "title": "Installed Software: Software Path",
            "type": "string"
        },
        {
            "branched": true,
            "name": "installed_software.source",
            "title": "Installed Software: Source",
            "type": "string"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "cve_id",
                        "title": "CVE ID",
                        "type": "string"
                    },
                    {
                        "name": "software_name",
                        "title": "Software Name",
                        "type": "string"
                    },
                    {
                        "format": "version",
                        "name": "software_version",
                        "title": "Software Version",
                        "type": "string"
                    },
                    {
                        "name": "software_vendor",
                        "title": "Software Vendor",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "v2.0",
                            "v3.0"
                        ],
                        "name": "cvss_version",
                        "title": "CVSS Version",
                        "type": "string"
                    },
                    {
                        "name": "cvss",
                        "title": "CVSS",
                        "type": "number"
                    },
                    {
                        "name": "cvss_str",
                        "title": "CVSS String",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "NONE",
                            "LOW",
                            "MEDIUM",
                            "HIGH",
                            "CRITICAL"
                        ],
                        "name": "cve_severity",
                        "title": "CVE Severity",
                        "type": "string"
                    },
                    {
                        "name": "cve_description",
                        "title": "CVE Description",
                        "type": "string"
                    },
                    {
                        "name": "cve_synopsis",
                        "title": "CVE Synopsis",
                        "type": "string"
                    },
                    {
                        "items": {
                            "type": "string"
                        },
                        "name": "cve_references",
                        "title": "CVE References",
                        "type": "array"
                    }
                ],
                "type": "array"
            },
            "name": "software_cves",
            "title": "Vulnerable Software",
            "type": "array"
        },
        {
            "branched": true,
            "name": "software_cves.cve_id",
            "title": "Vulnerable Software: CVE ID",
            "type": "string"
        },
        {
            "branched": true,
            "name": "software_cves.software_name",
            "title": "Vulnerable Software: Software Name",
            "type": "string"
        },
        {
            "branched": true,
            "format": "version",
            "name": "software_cves.software_version",
            "title": "Vulnerable Software: Software Version",
            "type": "string"
        },
        {
            "branched": true,
            "name": "software_cves.software_vendor",
            "title": "Vulnerable Software: Software Vendor",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "v2.0",
                "v3.0"
            ],
            "name": "software_cves.cvss_version",
            "title": "Vulnerable Software: CVSS Version",
            "type": "string"
        },
        {
            "branched": true,
            "name": "software_cves.cvss",
            "title": "Vulnerable Software: CVSS",
            "type": "number"
        },
        {
            "branched": true,
            "name": "software_cves.cvss_str",
            "title": "Vulnerable Software: CVSS String",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "NONE",
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL"
            ],
            "name": "software_cves.cve_severity",
            "title": "Vulnerable Software: CVE Severity",
            "type": "string"
        },
        {
            "branched": true,
            "name": "software_cves.cve_description",
            "title": "Vulnerable Software: CVE Description",
            "type": "string"
        },
        {
            "branched": true,
            "name": "software_cves.cve_synopsis",
            "title": "Vulnerable Software: CVE Synopsis",
            "type": "string"
        },
        {
            "items": {
                "type": "string"
            },
            "name": "software_cves.cve_references",
            "title": "Vulnerable Software: CVE References",
            "type": "array"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "security_patch_id",
                        "title": "Security Patch Name",
                        "type": "string"
                    },
                    {
                        "name": "patch_description",
                        "title": "Patch Description",
                        "type": "string"
                    },
                    {
                        "name": "classification",
                        "title": "Classification",
                        "type": "string"
                    },
                    {
                        "name": "state",
                        "title": "State",
                        "type": "string"
                    },
                    {
                        "name": "severity",
                        "title": "Severity",
                        "type": "string"
                    },
                    {
                        "name": "bulletin_id",
                        "title": "Bulletin ID",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "security_patches",
            "title": "OS Installed Security Patches",
            "type": "array"
        },
        {
            "branched": true,
            "name": "security_patches.security_patch_id",
            "title": "OS Installed Security Patches: Security Patch Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "security_patches.patch_description",
            "title": "OS Installed Security Patches: Patch Description",
            "type": "string"
        },
        {
            "branched": true,
            "name": "security_patches.classification",
            "title": "OS Installed Security Patches: Classification",
            "type": "string"
        },
        {
            "branched": true,
            "name": "security_patches.state",
            "title": "OS Installed Security Patches: State",
            "type": "string"
        },
        {
            "branched": true,
            "name": "security_patches.severity",
            "title": "OS Installed Security Patches: Severity",
            "type": "string"
        },
        {
            "branched": true,
            "name": "security_patches.bulletin_id",
            "title": "OS Installed Security Patches: Bulletin ID",
            "type": "string"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Name",
                        "type": "string"
                    },
                    {
                        "name": "manufacturer",
                        "title": "Manufacturer",
                        "type": "string"
                    },
                    {
                        "name": "hw_id",
                        "title": "ID",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "connected_hardware",
            "title": "Connected Hardware",
            "type": "array"
        },
        {
            "branched": true,
            "name": "connected_hardware.name",
            "title": "Connected Hardware: Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_hardware.manufacturer",
            "title": "Connected Hardware: Manufacturer",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_hardware.hw_id",
            "title": "Connected Hardware: ID",
            "type": "string"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "remote_name",
                        "title": "Remote Device Name",
                        "type": "string"
                    },
                    {
                        "items": {
                            "items": [
                                {
                                    "name": "name",
                                    "title": "Iface Name",
                                    "type": "string"
                                },
                                {
                                    "name": "mac",
                                    "title": "MAC",
                                    "type": "string"
                                },
                                {
                                    "name": "manufacturer",
                                    "title": "Manufacturer",
                                    "type": "string"
                                },
                                {
                                    "format": "ip",
                                    "items": {
                                        "format": "ip",
                                        "type": "string"
                                    },
                                    "name": "ips",
                                    "title": "IPs",
                                    "type": "array"
                                },
                                {
                                    "description": "Recognized Geo locations of the IPs",
                                    "items": {
                                        "type": "string"
                                    },
                                    "name": "locations",
                                    "title": "Locations",
                                    "type": "array"
                                },
                                {
                                    "description": "A list of subnets in ip format, that correspond the IPs",
                                    "format": "subnet",
                                    "items": {
                                        "format": "subnet",
                                        "type": "string"
                                    },
                                    "name": "subnets",
                                    "title": "Subnets",
                                    "type": "array"
                                },
                                {
                                    "description": "A list of vlans in this interface",
                                    "items": {
                                        "items": [
                                            {
                                                "name": "name",
                                                "title": "Vlan Name",
                                                "type": "string"
                                            },
                                            {
                                                "name": "tagid",
                                                "title": "Tag ID",
                                                "type": "integer"
                                            },
                                            {
                                                "enum": [
                                                    "Tagged",
                                                    "Untagged"
                                                ],
                                                "name": "tagness",
                                                "title": "Vlan Tagness",
                                                "type": "string"
                                            }
                                        ],
                                        "type": "array"
                                    },
                                    "name": "vlan_list",
                                    "title": "Vlans",
                                    "type": "array"
                                },
                                {
                                    "branched": true,
                                    "name": "vlan_list.name",
                                    "title": "Vlans: Vlan Name",
                                    "type": "string"
                                },
                                {
                                    "branched": true,
                                    "name": "vlan_list.tagid",
                                    "title": "Vlans: Tag ID",
                                    "type": "integer"
                                },
                                {
                                    "branched": true,
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ],
                                    "name": "vlan_list.tagness",
                                    "title": "Vlans: Vlan Tagness",
                                    "type": "string"
                                },
                                {
                                    "enum": [
                                        "Up",
                                        "Down",
                                        "Testing",
                                        "Unknown",
                                        "Dormant",
                                        "Nonpresent",
                                        "LowerLayerDown"
                                    ],
                                    "name": "operational_status",
                                    "title": "Operational Status",
                                    "type": "string"
                                },
                                {
                                    "enum": [
                                        "Up",
                                        "Down",
                                        "Testing"
                                    ],
                                    "name": "admin_status",
                                    "title": "Admin Status",
                                    "type": "string"
                                },
                                {
                                    "description": "Interface max speed per Second",
                                    "name": "speed",
                                    "title": "Interface Speed",
                                    "type": "string"
                                },
                                {
                                    "enum": [
                                        "Access",
                                        "Trunk"
                                    ],
                                    "name": "port_type",
                                    "title": "Port Type",
                                    "type": "string"
                                },
                                {
                                    "description": "Interface Maximum transmission unit",
                                    "name": "mtu",
                                    "title": "MTU",
                                    "type": "string"
                                },
                                {
                                    "name": "gateway",
                                    "title": "Gateway",
                                    "type": "string"
                                },
                                {
                                    "name": "port",
                                    "title": "Port",
                                    "type": "string"
                                }
                            ],
                            "type": "array"
                        },
                        "name": "local_ifaces",
                        "title": "Local Interface",
                        "type": "array"
                    },
                    {
                        "branched": true,
                        "name": "local_ifaces.name",
                        "title": "Local Interface: Iface Name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "local_ifaces.mac",
                        "title": "Local Interface: MAC",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "local_ifaces.manufacturer",
                        "title": "Local Interface: Manufacturer",
                        "type": "string"
                    },
                    {
                        "format": "ip",
                        "items": {
                            "format": "ip",
                            "type": "string"
                        },
                        "name": "local_ifaces.ips",
                        "title": "Local Interface: IPs",
                        "type": "array"
                    },
                    {
                        "description": "Recognized Geo locations of the IPs",
                        "items": {
                            "type": "string"
                        },
                        "name": "local_ifaces.locations",
                        "title": "Local Interface: Locations",
                        "type": "array"
                    },
                    {
                        "description": "A list of subnets in ip format, that correspond the IPs",
                        "format": "subnet",
                        "items": {
                            "format": "subnet",
                            "type": "string"
                        },
                        "name": "local_ifaces.subnets",
                        "title": "Local Interface: Subnets",
                        "type": "array"
                    },
                    {
                        "description": "A list of vlans in this interface",
                        "items": {
                            "items": [
                                {
                                    "name": "name",
                                    "title": "Vlan Name",
                                    "type": "string"
                                },
                                {
                                    "name": "tagid",
                                    "title": "Tag ID",
                                    "type": "integer"
                                },
                                {
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ],
                                    "name": "tagness",
                                    "title": "Vlan Tagness",
                                    "type": "string"
                                }
                            ],
                            "type": "array"
                        },
                        "name": "local_ifaces.vlan_list",
                        "title": "Local Interface: Vlans",
                        "type": "array"
                    },
                    {
                        "branched": true,
                        "name": "local_ifaces.vlan_list.name",
                        "title": "Local Interface: Vlans: Vlan Name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "local_ifaces.vlan_list.tagid",
                        "title": "Local Interface: Vlans: Tag ID",
                        "type": "integer"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ],
                        "name": "local_ifaces.vlan_list.tagness",
                        "title": "Local Interface: Vlans: Vlan Tagness",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Up",
                            "Down",
                            "Testing",
                            "Unknown",
                            "Dormant",
                            "Nonpresent",
                            "LowerLayerDown"
                        ],
                        "name": "local_ifaces.operational_status",
                        "title": "Local Interface: Operational Status",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Up",
                            "Down",
                            "Testing"
                        ],
                        "name": "local_ifaces.admin_status",
                        "title": "Local Interface: Admin Status",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "description": "Interface max speed per Second",
                        "name": "local_ifaces.speed",
                        "title": "Local Interface: Interface Speed",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Access",
                            "Trunk"
                        ],
                        "name": "local_ifaces.port_type",
                        "title": "Local Interface: Port Type",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "description": "Interface Maximum transmission unit",
                        "name": "local_ifaces.mtu",
                        "title": "Local Interface: MTU",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "local_ifaces.gateway",
                        "title": "Local Interface: Gateway",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "local_ifaces.port",
                        "title": "Local Interface: Port",
                        "type": "string"
                    },
                    {
                        "items": {
                            "items": [
                                {
                                    "name": "name",
                                    "title": "Iface Name",
                                    "type": "string"
                                },
                                {
                                    "name": "mac",
                                    "title": "MAC",
                                    "type": "string"
                                },
                                {
                                    "name": "manufacturer",
                                    "title": "Manufacturer",
                                    "type": "string"
                                },
                                {
                                    "format": "ip",
                                    "items": {
                                        "format": "ip",
                                        "type": "string"
                                    },
                                    "name": "ips",
                                    "title": "IPs",
                                    "type": "array"
                                },
                                {
                                    "description": "Recognized Geo locations of the IPs",
                                    "items": {
                                        "type": "string"
                                    },
                                    "name": "locations",
                                    "title": "Locations",
                                    "type": "array"
                                },
                                {
                                    "description": "A list of subnets in ip format, that correspond the IPs",
                                    "format": "subnet",
                                    "items": {
                                        "format": "subnet",
                                        "type": "string"
                                    },
                                    "name": "subnets",
                                    "title": "Subnets",
                                    "type": "array"
                                },
                                {
                                    "description": "A list of vlans in this interface",
                                    "items": {
                                        "items": [
                                            {
                                                "name": "name",
                                                "title": "Vlan Name",
                                                "type": "string"
                                            },
                                            {
                                                "name": "tagid",
                                                "title": "Tag ID",
                                                "type": "integer"
                                            },
                                            {
                                                "enum": [
                                                    "Tagged",
                                                    "Untagged"
                                                ],
                                                "name": "tagness",
                                                "title": "Vlan Tagness",
                                                "type": "string"
                                            }
                                        ],
                                        "type": "array"
                                    },
                                    "name": "vlan_list",
                                    "title": "Vlans",
                                    "type": "array"
                                },
                                {
                                    "branched": true,
                                    "name": "vlan_list.name",
                                    "title": "Vlans: Vlan Name",
                                    "type": "string"
                                },
                                {
                                    "branched": true,
                                    "name": "vlan_list.tagid",
                                    "title": "Vlans: Tag ID",
                                    "type": "integer"
                                },
                                {
                                    "branched": true,
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ],
                                    "name": "vlan_list.tagness",
                                    "title": "Vlans: Vlan Tagness",
                                    "type": "string"
                                },
                                {
                                    "enum": [
                                        "Up",
                                        "Down",
                                        "Testing",
                                        "Unknown",
                                        "Dormant",
                                        "Nonpresent",
                                        "LowerLayerDown"
                                    ],
                                    "name": "operational_status",
                                    "title": "Operational Status",
                                    "type": "string"
                                },
                                {
                                    "enum": [
                                        "Up",
                                        "Down",
                                        "Testing"
                                    ],
                                    "name": "admin_status",
                                    "title": "Admin Status",
                                    "type": "string"
                                },
                                {
                                    "description": "Interface max speed per Second",
                                    "name": "speed",
                                    "title": "Interface Speed",
                                    "type": "string"
                                },
                                {
                                    "enum": [
                                        "Access",
                                        "Trunk"
                                    ],
                                    "name": "port_type",
                                    "title": "Port Type",
                                    "type": "string"
                                },
                                {
                                    "description": "Interface Maximum transmission unit",
                                    "name": "mtu",
                                    "title": "MTU",
                                    "type": "string"
                                },
                                {
                                    "name": "gateway",
                                    "title": "Gateway",
                                    "type": "string"
                                },
                                {
                                    "name": "port",
                                    "title": "Port",
                                    "type": "string"
                                }
                            ],
                            "type": "array"
                        },
                        "name": "remote_ifaces",
                        "title": "Remote Device Iface",
                        "type": "array"
                    },
                    {
                        "branched": true,
                        "name": "remote_ifaces.name",
                        "title": "Remote Device Iface: Iface Name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "remote_ifaces.mac",
                        "title": "Remote Device Iface: MAC",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "remote_ifaces.manufacturer",
                        "title": "Remote Device Iface: Manufacturer",
                        "type": "string"
                    },
                    {
                        "format": "ip",
                        "items": {
                            "format": "ip",
                            "type": "string"
                        },
                        "name": "remote_ifaces.ips",
                        "title": "Remote Device Iface: IPs",
                        "type": "array"
                    },
                    {
                        "description": "Recognized Geo locations of the IPs",
                        "items": {
                            "type": "string"
                        },
                        "name": "remote_ifaces.locations",
                        "title": "Remote Device Iface: Locations",
                        "type": "array"
                    },
                    {
                        "description": "A list of subnets in ip format, that correspond the IPs",
                        "format": "subnet",
                        "items": {
                            "format": "subnet",
                            "type": "string"
                        },
                        "name": "remote_ifaces.subnets",
                        "title": "Remote Device Iface: Subnets",
                        "type": "array"
                    },
                    {
                        "description": "A list of vlans in this interface",
                        "items": {
                            "items": [
                                {
                                    "name": "name",
                                    "title": "Vlan Name",
                                    "type": "string"
                                },
                                {
                                    "name": "tagid",
                                    "title": "Tag ID",
                                    "type": "integer"
                                },
                                {
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ],
                                    "name": "tagness",
                                    "title": "Vlan Tagness",
                                    "type": "string"
                                }
                            ],
                            "type": "array"
                        },
                        "name": "remote_ifaces.vlan_list",
                        "title": "Remote Device Iface: Vlans",
                        "type": "array"
                    },
                    {
                        "branched": true,
                        "name": "remote_ifaces.vlan_list.name",
                        "title": "Remote Device Iface: Vlans: Vlan Name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "remote_ifaces.vlan_list.tagid",
                        "title": "Remote Device Iface: Vlans: Tag ID",
                        "type": "integer"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ],
                        "name": "remote_ifaces.vlan_list.tagness",
                        "title": "Remote Device Iface: Vlans: Vlan Tagness",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Up",
                            "Down",
                            "Testing",
                            "Unknown",
                            "Dormant",
                            "Nonpresent",
                            "LowerLayerDown"
                        ],
                        "name": "remote_ifaces.operational_status",
                        "title": "Remote Device Iface: Operational Status",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Up",
                            "Down",
                            "Testing"
                        ],
                        "name": "remote_ifaces.admin_status",
                        "title": "Remote Device Iface: Admin Status",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "description": "Interface max speed per Second",
                        "name": "remote_ifaces.speed",
                        "title": "Remote Device Iface: Interface Speed",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Access",
                            "Trunk"
                        ],
                        "name": "remote_ifaces.port_type",
                        "title": "Remote Device Iface: Port Type",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "description": "Interface Maximum transmission unit",
                        "name": "remote_ifaces.mtu",
                        "title": "Remote Device Iface: MTU",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "remote_ifaces.gateway",
                        "title": "Remote Device Iface: Gateway",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "remote_ifaces.port",
                        "title": "Remote Device Iface: Port",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Direct",
                            "Indirect"
                        ],
                        "name": "connection_type",
                        "title": "Connection Type",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "connected_devices",
            "title": "Connected Devices",
            "type": "array"
        },
        {
            "branched": true,
            "name": "connected_devices.remote_name",
            "title": "Connected Devices: Remote Device Name",
            "type": "string"
        },
        {
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Iface Name",
                        "type": "string"
                    },
                    {
                        "name": "mac",
                        "title": "MAC",
                        "type": "string"
                    },
                    {
                        "name": "manufacturer",
                        "title": "Manufacturer",
                        "type": "string"
                    },
                    {
                        "format": "ip",
                        "items": {
                            "format": "ip",
                            "type": "string"
                        },
                        "name": "ips",
                        "title": "IPs",
                        "type": "array"
                    },
                    {
                        "description": "Recognized Geo locations of the IPs",
                        "items": {
                            "type": "string"
                        },
                        "name": "locations",
                        "title": "Locations",
                        "type": "array"
                    },
                    {
                        "description": "A list of subnets in ip format, that correspond the IPs",
                        "format": "subnet",
                        "items": {
                            "format": "subnet",
                            "type": "string"
                        },
                        "name": "subnets",
                        "title": "Subnets",
                        "type": "array"
                    },
                    {
                        "description": "A list of vlans in this interface",
                        "items": {
                            "items": [
                                {
                                    "name": "name",
                                    "title": "Vlan Name",
                                    "type": "string"
                                },
                                {
                                    "name": "tagid",
                                    "title": "Tag ID",
                                    "type": "integer"
                                },
                                {
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ],
                                    "name": "tagness",
                                    "title": "Vlan Tagness",
                                    "type": "string"
                                }
                            ],
                            "type": "array"
                        },
                        "name": "vlan_list",
                        "title": "Vlans",
                        "type": "array"
                    },
                    {
                        "branched": true,
                        "name": "vlan_list.name",
                        "title": "Vlans: Vlan Name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "vlan_list.tagid",
                        "title": "Vlans: Tag ID",
                        "type": "integer"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ],
                        "name": "vlan_list.tagness",
                        "title": "Vlans: Vlan Tagness",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Up",
                            "Down",
                            "Testing",
                            "Unknown",
                            "Dormant",
                            "Nonpresent",
                            "LowerLayerDown"
                        ],
                        "name": "operational_status",
                        "title": "Operational Status",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Up",
                            "Down",
                            "Testing"
                        ],
                        "name": "admin_status",
                        "title": "Admin Status",
                        "type": "string"
                    },
                    {
                        "description": "Interface max speed per Second",
                        "name": "speed",
                        "title": "Interface Speed",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Access",
                            "Trunk"
                        ],
                        "name": "port_type",
                        "title": "Port Type",
                        "type": "string"
                    },
                    {
                        "description": "Interface Maximum transmission unit",
                        "name": "mtu",
                        "title": "MTU",
                        "type": "string"
                    },
                    {
                        "name": "gateway",
                        "title": "Gateway",
                        "type": "string"
                    },
                    {
                        "name": "port",
                        "title": "Port",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "connected_devices.local_ifaces",
            "title": "Connected Devices: Local Interface",
            "type": "array"
        },
        {
            "branched": true,
            "name": "connected_devices.local_ifaces.name",
            "title": "Connected Devices: Local Interface: Iface Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_devices.local_ifaces.mac",
            "title": "Connected Devices: Local Interface: MAC",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_devices.local_ifaces.manufacturer",
            "title": "Connected Devices: Local Interface: Manufacturer",
            "type": "string"
        },
        {
            "format": "ip",
            "items": {
                "format": "ip",
                "type": "string"
            },
            "name": "connected_devices.local_ifaces.ips",
            "title": "Connected Devices: Local Interface: IPs",
            "type": "array"
        },
        {
            "description": "Recognized Geo locations of the IPs",
            "items": {
                "type": "string"
            },
            "name": "connected_devices.local_ifaces.locations",
            "title": "Connected Devices: Local Interface: Locations",
            "type": "array"
        },
        {
            "description": "A list of subnets in ip format, that correspond the IPs",
            "format": "subnet",
            "items": {
                "format": "subnet",
                "type": "string"
            },
            "name": "connected_devices.local_ifaces.subnets",
            "title": "Connected Devices: Local Interface: Subnets",
            "type": "array"
        },
        {
            "description": "A list of vlans in this interface",
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Vlan Name",
                        "type": "string"
                    },
                    {
                        "name": "tagid",
                        "title": "Tag ID",
                        "type": "integer"
                    },
                    {
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ],
                        "name": "tagness",
                        "title": "Vlan Tagness",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "connected_devices.local_ifaces.vlan_list",
            "title": "Connected Devices: Local Interface: Vlans",
            "type": "array"
        },
        {
            "branched": true,
            "name": "connected_devices.local_ifaces.vlan_list.name",
            "title": "Connected Devices: Local Interface: Vlans: Vlan Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_devices.local_ifaces.vlan_list.tagid",
            "title": "Connected Devices: Local Interface: Vlans: Tag ID",
            "type": "integer"
        },
        {
            "branched": true,
            "enum": [
                "Tagged",
                "Untagged"
            ],
            "name": "connected_devices.local_ifaces.vlan_list.tagness",
            "title": "Connected Devices: Local Interface: Vlans: Vlan Tagness",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Up",
                "Down",
                "Testing",
                "Unknown",
                "Dormant",
                "Nonpresent",
                "LowerLayerDown"
            ],
            "name": "connected_devices.local_ifaces.operational_status",
            "title": "Connected Devices: Local Interface: Operational Status",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Up",
                "Down",
                "Testing"
            ],
            "name": "connected_devices.local_ifaces.admin_status",
            "title": "Connected Devices: Local Interface: Admin Status",
            "type": "string"
        },
        {
            "branched": true,
            "description": "Interface max speed per Second",
            "name": "connected_devices.local_ifaces.speed",
            "title": "Connected Devices: Local Interface: Interface Speed",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Access",
                "Trunk"
            ],
            "name": "connected_devices.local_ifaces.port_type",
            "title": "Connected Devices: Local Interface: Port Type",
            "type": "string"
        },
        {
            "branched": true,
            "description": "Interface Maximum transmission unit",
            "name": "connected_devices.local_ifaces.mtu",
            "title": "Connected Devices: Local Interface: MTU",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_devices.local_ifaces.gateway",
            "title": "Connected Devices: Local Interface: Gateway",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_devices.local_ifaces.port",
            "title": "Connected Devices: Local Interface: Port",
            "type": "string"
        },
        {
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Iface Name",
                        "type": "string"
                    },
                    {
                        "name": "mac",
                        "title": "MAC",
                        "type": "string"
                    },
                    {
                        "name": "manufacturer",
                        "title": "Manufacturer",
                        "type": "string"
                    },
                    {
                        "format": "ip",
                        "items": {
                            "format": "ip",
                            "type": "string"
                        },
                        "name": "ips",
                        "title": "IPs",
                        "type": "array"
                    },
                    {
                        "description": "Recognized Geo locations of the IPs",
                        "items": {
                            "type": "string"
                        },
                        "name": "locations",
                        "title": "Locations",
                        "type": "array"
                    },
                    {
                        "description": "A list of subnets in ip format, that correspond the IPs",
                        "format": "subnet",
                        "items": {
                            "format": "subnet",
                            "type": "string"
                        },
                        "name": "subnets",
                        "title": "Subnets",
                        "type": "array"
                    },
                    {
                        "description": "A list of vlans in this interface",
                        "items": {
                            "items": [
                                {
                                    "name": "name",
                                    "title": "Vlan Name",
                                    "type": "string"
                                },
                                {
                                    "name": "tagid",
                                    "title": "Tag ID",
                                    "type": "integer"
                                },
                                {
                                    "enum": [
                                        "Tagged",
                                        "Untagged"
                                    ],
                                    "name": "tagness",
                                    "title": "Vlan Tagness",
                                    "type": "string"
                                }
                            ],
                            "type": "array"
                        },
                        "name": "vlan_list",
                        "title": "Vlans",
                        "type": "array"
                    },
                    {
                        "branched": true,
                        "name": "vlan_list.name",
                        "title": "Vlans: Vlan Name",
                        "type": "string"
                    },
                    {
                        "branched": true,
                        "name": "vlan_list.tagid",
                        "title": "Vlans: Tag ID",
                        "type": "integer"
                    },
                    {
                        "branched": true,
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ],
                        "name": "vlan_list.tagness",
                        "title": "Vlans: Vlan Tagness",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Up",
                            "Down",
                            "Testing",
                            "Unknown",
                            "Dormant",
                            "Nonpresent",
                            "LowerLayerDown"
                        ],
                        "name": "operational_status",
                        "title": "Operational Status",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Up",
                            "Down",
                            "Testing"
                        ],
                        "name": "admin_status",
                        "title": "Admin Status",
                        "type": "string"
                    },
                    {
                        "description": "Interface max speed per Second",
                        "name": "speed",
                        "title": "Interface Speed",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Access",
                            "Trunk"
                        ],
                        "name": "port_type",
                        "title": "Port Type",
                        "type": "string"
                    },
                    {
                        "description": "Interface Maximum transmission unit",
                        "name": "mtu",
                        "title": "MTU",
                        "type": "string"
                    },
                    {
                        "name": "gateway",
                        "title": "Gateway",
                        "type": "string"
                    },
                    {
                        "name": "port",
                        "title": "Port",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "connected_devices.remote_ifaces",
            "title": "Connected Devices: Remote Device Iface",
            "type": "array"
        },
        {
            "branched": true,
            "name": "connected_devices.remote_ifaces.name",
            "title": "Connected Devices: Remote Device Iface: Iface Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_devices.remote_ifaces.mac",
            "title": "Connected Devices: Remote Device Iface: MAC",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_devices.remote_ifaces.manufacturer",
            "title": "Connected Devices: Remote Device Iface: Manufacturer",
            "type": "string"
        },
        {
            "format": "ip",
            "items": {
                "format": "ip",
                "type": "string"
            },
            "name": "connected_devices.remote_ifaces.ips",
            "title": "Connected Devices: Remote Device Iface: IPs",
            "type": "array"
        },
        {
            "description": "Recognized Geo locations of the IPs",
            "items": {
                "type": "string"
            },
            "name": "connected_devices.remote_ifaces.locations",
            "title": "Connected Devices: Remote Device Iface: Locations",
            "type": "array"
        },
        {
            "description": "A list of subnets in ip format, that correspond the IPs",
            "format": "subnet",
            "items": {
                "format": "subnet",
                "type": "string"
            },
            "name": "connected_devices.remote_ifaces.subnets",
            "title": "Connected Devices: Remote Device Iface: Subnets",
            "type": "array"
        },
        {
            "description": "A list of vlans in this interface",
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Vlan Name",
                        "type": "string"
                    },
                    {
                        "name": "tagid",
                        "title": "Tag ID",
                        "type": "integer"
                    },
                    {
                        "enum": [
                            "Tagged",
                            "Untagged"
                        ],
                        "name": "tagness",
                        "title": "Vlan Tagness",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "connected_devices.remote_ifaces.vlan_list",
            "title": "Connected Devices: Remote Device Iface: Vlans",
            "type": "array"
        },
        {
            "branched": true,
            "name": "connected_devices.remote_ifaces.vlan_list.name",
            "title": "Connected Devices: Remote Device Iface: Vlans: Vlan Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_devices.remote_ifaces.vlan_list.tagid",
            "title": "Connected Devices: Remote Device Iface: Vlans: Tag ID",
            "type": "integer"
        },
        {
            "branched": true,
            "enum": [
                "Tagged",
                "Untagged"
            ],
            "name": "connected_devices.remote_ifaces.vlan_list.tagness",
            "title": "Connected Devices: Remote Device Iface: Vlans: Vlan Tagness",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Up",
                "Down",
                "Testing",
                "Unknown",
                "Dormant",
                "Nonpresent",
                "LowerLayerDown"
            ],
            "name": "connected_devices.remote_ifaces.operational_status",
            "title": "Connected Devices: Remote Device Iface: Operational Status",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Up",
                "Down",
                "Testing"
            ],
            "name": "connected_devices.remote_ifaces.admin_status",
            "title": "Connected Devices: Remote Device Iface: Admin Status",
            "type": "string"
        },
        {
            "branched": true,
            "description": "Interface max speed per Second",
            "name": "connected_devices.remote_ifaces.speed",
            "title": "Connected Devices: Remote Device Iface: Interface Speed",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Access",
                "Trunk"
            ],
            "name": "connected_devices.remote_ifaces.port_type",
            "title": "Connected Devices: Remote Device Iface: Port Type",
            "type": "string"
        },
        {
            "branched": true,
            "description": "Interface Maximum transmission unit",
            "name": "connected_devices.remote_ifaces.mtu",
            "title": "Connected Devices: Remote Device Iface: MTU",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_devices.remote_ifaces.gateway",
            "title": "Connected Devices: Remote Device Iface: Gateway",
            "type": "string"
        },
        {
            "branched": true,
            "name": "connected_devices.remote_ifaces.port",
            "title": "Connected Devices: Remote Device Iface: Port",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Direct",
                "Indirect"
            ],
            "name": "connected_devices.connection_type",
            "title": "Connected Devices: Connection Type",
            "type": "string"
        },
        {
            "name": "id",
            "title": "ID",
            "type": "string"
        },
        {
            "name": "part_of_domain",
            "title": "Part Of Domain",
            "type": "bool"
        },
        {
            "name": "domain",
            "title": "Domain",
            "type": "string"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "user_sid",
                        "title": "SID",
                        "type": "string"
                    },
                    {
                        "name": "username",
                        "title": "Username",
                        "type": "string"
                    },
                    {
                        "format": "date-time",
                        "name": "last_use_date",
                        "title": "Last Use Time",
                        "type": "string"
                    },
                    {
                        "name": "is_local",
                        "title": "Is Local",
                        "type": "bool"
                    },
                    {
                        "name": "is_disabled",
                        "title": "Is Disabled",
                        "type": "bool"
                    },
                    {
                        "name": "is_admin",
                        "title": "Is Admin",
                        "type": "bool"
                    },
                    {
                        "name": "user_department",
                        "title": "Department",
                        "type": "string"
                    },
                    {
                        "name": "password_max_age",
                        "title": "Password Max Age",
                        "type": "integer"
                    },
                    {
                        "name": "interpreter",
                        "title": "Interpreter",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "users",
            "title": "Users",
            "type": "array"
        },
        {
            "branched": true,
            "name": "users.user_sid",
            "title": "Users: SID",
            "type": "string"
        },
        {
            "branched": true,
            "name": "users.username",
            "title": "Users: Username",
            "type": "string"
        },
        {
            "branched": true,
            "format": "date-time",
            "name": "users.last_use_date",
            "title": "Users: Last Use Time",
            "type": "string"
        },
        {
            "branched": true,
            "name": "users.is_local",
            "title": "Users: Is Local",
            "type": "bool"
        },
        {
            "branched": true,
            "name": "users.is_disabled",
            "title": "Users: Is Disabled",
            "type": "bool"
        },
        {
            "branched": true,
            "name": "users.is_admin",
            "title": "Users: Is Admin",
            "type": "bool"
        },
        {
            "branched": true,
            "name": "users.user_department",
            "title": "Users: Department",
            "type": "string"
        },
        {
            "branched": true,
            "name": "users.password_max_age",
            "title": "Users: Password Max Age",
            "type": "integer"
        },
        {
            "branched": true,
            "name": "users.interpreter",
            "title": "Users: Interpreter",
            "type": "string"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "admin_name",
                        "title": "Name of user or group",
                        "type": "string"
                    },
                    {
                        "enum": [
                            "Group Membership",
                            "Admin User"
                        ],
                        "name": "admin_type",
                        "title": "Admin Type",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "local_admins",
            "title": "Local Admins",
            "type": "array"
        },
        {
            "branched": true,
            "name": "local_admins.admin_name",
            "title": "Local Admins: Name of user or group",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                "Group Membership",
                "Admin User"
            ],
            "name": "local_admins.admin_type",
            "title": "Local Admins: Admin Type",
            "type": "string"
        },
        {
            "items": {
                "type": "string"
            },
            "name": "local_admins_users",
            "title": "Local Admins - Users",
            "type": "array"
        },
        {
            "items": {
                "type": "string"
            },
            "name": "local_admins_groups",
            "title": "Local Admins - Groups",
            "type": "array"
        },
        {
            "enum": [
                "Unspecified",
                "Desktop",
                "Laptop or Tablet",
                "Workstation",
                "Enterprise Server",
                "SOHO Server",
                "Appliance PC",
                "Performance Server",
                "Maximum",
                "Mobile"
            ],
            "name": "pc_type",
            "title": "PC Type",
            "type": "string"
        },
        {
            "name": "number_of_processes",
            "title": "Number Of Processes",
            "type": "integer"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "path",
                        "title": "Path",
                        "type": "string"
                    },
                    {
                        "name": "device",
                        "title": "Device Name",
                        "type": "string"
                    },
                    {
                        "name": "file_system",
                        "title": "Filesystem",
                        "type": "string"
                    },
                    {
                        "name": "total_size",
                        "title": "Size (GB)",
                        "type": "number"
                    },
                    {
                        "name": "free_size",
                        "title": "Free Size (GB)",
                        "type": "number"
                    },
                    {
                        "name": "is_encrypted",
                        "title": "Encrypted",
                        "type": "bool"
                    },
                    {
                        "name": "description",
                        "title": "Description",
                        "type": "string"
                    },
                    {
                        "name": "serial_number",
                        "title": "Serial Number",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "hard_drives",
            "title": "Hard Drives",
            "type": "array"
        },
        {
            "branched": true,
            "name": "hard_drives.path",
            "title": "Hard Drives: Path",
            "type": "string"
        },
        {
            "branched": true,
            "name": "hard_drives.device",
            "title": "Hard Drives: Device Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "hard_drives.file_system",
            "title": "Hard Drives: Filesystem",
            "type": "string"
        },
        {
            "branched": true,
            "name": "hard_drives.total_size",
            "title": "Hard Drives: Size (GB)",
            "type": "number"
        },
        {
            "branched": true,
            "name": "hard_drives.free_size",
            "title": "Hard Drives: Free Size (GB)",
            "type": "number"
        },
        {
            "branched": true,
            "name": "hard_drives.is_encrypted",
            "title": "Hard Drives: Encrypted",
            "type": "bool"
        },
        {
            "branched": true,
            "name": "hard_drives.description",
            "title": "Hard Drives: Description",
            "type": "string"
        },
        {
            "branched": true,
            "name": "hard_drives.serial_number",
            "title": "Hard Drives: Serial Number",
            "type": "string"
        },
        {
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Description",
                        "type": "string"
                    },
                    {
                        "name": "manufacturer",
                        "title": "Manufacturer",
                        "type": "string"
                    },
                    {
                        "enum": [
                            32,
                            64
                        ],
                        "name": "bitness",
                        "title": "Bitness",
                        "type": "integer"
                    },
                    {
                        "name": "family",
                        "title": "Family",
                        "type": "string"
                    },
                    {
                        "name": "cores",
                        "title": "Cores",
                        "type": "integer"
                    },
                    {
                        "name": "cores_thread",
                        "title": "Threads in core",
                        "type": "integer"
                    },
                    {
                        "name": "load_percentage",
                        "title": "Load Percentage",
                        "type": "integer"
                    },
                    {
                        "enum": [
                            "x86",
                            "x64",
                            "MIPS",
                            "Alpha",
                            "PowerPC",
                            "ARM",
                            "ia64"
                        ],
                        "name": "architecture",
                        "title": "Architecture",
                        "type": "string"
                    },
                    {
                        "name": "ghz",
                        "title": "Clockspeed (GHZ)",
                        "type": "number"
                    }
                ],
                "type": "array"
            },
            "name": "cpus",
            "title": "CPUs",
            "type": "array"
        },
        {
            "branched": true,
            "name": "cpus.name",
            "title": "CPUs: Description",
            "type": "string"
        },
        {
            "branched": true,
            "name": "cpus.manufacturer",
            "title": "CPUs: Manufacturer",
            "type": "string"
        },
        {
            "branched": true,
            "enum": [
                32,
                64
            ],
            "name": "cpus.bitness",
            "title": "CPUs: Bitness",
            "type": "integer"
        },
        {
            "branched": true,
            "name": "cpus.family",
            "title": "CPUs: Family",
            "type": "string"
        },
        {
            "branched": true,
            "name": "cpus.cores",
            "title": "CPUs: Cores",
            "type": "integer"
        },
        {
            "branched": true,
            "name": "cpus.cores_thread",
            "title": "CPUs: Threads in core",
            "type": "integer"
        },
        {
            "branched": true,
            "name": "cpus.load_percentage",
            "title": "CPUs: Load Percentage",
            "type": "integer"
        },
        {
            "branched": true,
            "enum": [
                "x86",
                "x64",
                "MIPS",
                "Alpha",
                "PowerPC",
                "ARM",
                "ia64"
            ],
            "name": "cpus.architecture",
            "title": "CPUs: Architecture",
            "type": "string"
        },
        {
            "branched": true,
            "name": "cpus.ghz",
            "title": "CPUs: Clockspeed (GHZ)",
            "type": "number"
        },
        {
            "name": "time_zone",
            "title": "Time Zone",
            "type": "string"
        },
        {
            "format": "date-time",
            "name": "boot_time",
            "title": "Boot Time",
            "type": "string"
        },
        {
            "name": "uptime",
            "title": "Uptime (Days)",
            "type": "integer"
        },
        {
            "name": "device_manufacturer",
            "title": "Device Manufacturer",
            "type": "string"
        },
        {
            "name": "device_model",
            "title": "Device Model",
            "type": "string"
        },
        {
            "name": "device_serial",
            "title": "Device Manufacturer Serial",
            "type": "string"
        },
        {
            "name": "bios_version",
            "title": "Bios Version",
            "type": "string"
        },
        {
            "name": "bios_serial",
            "title": "Bios Serial",
            "type": "string"
        },
        {
            "name": "total_physical_memory",
            "title": "Total RAM (GB)",
            "type": "number"
        },
        {
            "name": "free_physical_memory",
            "title": "Free RAM (GB)",
            "type": "number"
        },
        {
            "name": "physical_memory_percentage",
            "title": "RAM Usage (%)",
            "type": "number"
        },
        {
            "name": "total_number_of_physical_processors",
            "title": "Total Physical Processors",
            "type": "integer"
        },
        {
            "name": "total_number_of_cores",
            "title": "Total Cores",
            "type": "integer"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Name",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "processes",
            "title": "Running Processes",
            "type": "array"
        },
        {
            "branched": true,
            "name": "processes.name",
            "title": "Running Processes: Name",
            "type": "string"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Name",
                        "type": "string"
                    },
                    {
                        "name": "display_name",
                        "title": "Display Name",
                        "type": "string"
                    },
                    {
                        "name": "status",
                        "title": "Status",
                        "type": "string"
                    },
                    {
                        "name": "start_name",
                        "title": "Start Name",
                        "type": "string"
                    },
                    {
                        "name": "start_mode",
                        "title": "Start Mode",
                        "type": "string"
                    },
                    {
                        "name": "path_name",
                        "title": "Path Name",
                        "type": "string"
                    },
                    {
                        "name": "description",
                        "title": "Description",
                        "type": "string"
                    },
                    {
                        "name": "caption",
                        "title": "Caption",
                        "type": "string"
                    },
                    {
                        "name": "service_type",
                        "title": "Service Type",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "services",
            "title": "Services",
            "type": "array"
        },
        {
            "branched": true,
            "name": "services.name",
            "title": "Services: Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "services.display_name",
            "title": "Services: Display Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "services.status",
            "title": "Services: Status",
            "type": "string"
        },
        {
            "branched": true,
            "name": "services.start_name",
            "title": "Services: Start Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "services.start_mode",
            "title": "Services: Start Mode",
            "type": "string"
        },
        {
            "branched": true,
            "name": "services.path_name",
            "title": "Services: Path Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "services.description",
            "title": "Services: Description",
            "type": "string"
        },
        {
            "branched": true,
            "name": "services.caption",
            "title": "Services: Caption",
            "type": "string"
        },
        {
            "branched": true,
            "name": "services.service_type",
            "title": "Services: Service Type",
            "type": "string"
        },
        {
            "format": "table",
            "items": {
                "items": [
                    {
                        "name": "name",
                        "title": "Name",
                        "type": "string"
                    },
                    {
                        "name": "description",
                        "title": "Description",
                        "type": "string"
                    },
                    {
                        "name": "path",
                        "title": "Path",
                        "type": "string"
                    },
                    {
                        "name": "status",
                        "title": "Status",
                        "type": "string"
                    }
                ],
                "type": "array"
            },
            "name": "shares",
            "title": "Shares",
            "type": "array"
        },
        {
            "branched": true,
            "name": "shares.name",
            "title": "Shares: Name",
            "type": "string"
        },
        {
            "branched": true,
            "name": "shares.description",
            "title": "Shares: Description",
            "type": "string"
        },
        {
            "branched": true,
            "name": "shares.path",
            "title": "Shares: Path",
            "type": "string"
        },
        {
            "branched": true,
            "name": "shares.status",
            "title": "Shares: Status",
            "type": "string"
        },
        {
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
                "type": "string"
            },
            "name": "adapter_properties",
            "title": "Adapter Properties",
            "type": "array"
        },
        {
            "name": "adapter_count",
            "title": "Distinct Adapter Connections Count",
            "type": "number"
        }
    ],
    "raw_fields": []
    }''')
}
