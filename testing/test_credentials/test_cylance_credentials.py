from json_file_adapter.service import DEVICES_DATA, USERS_DATA, FILE_NAME
from test_helpers.file_mock_credentials import FileForCredentialsMock

client_details = {
    "domain": "protectapi.cylance.com",
    "app_id": "746b9de2-8a3b-4893-aab3-9219a43acbce",
    "app_secret": "68696b23-c4bb-4e4c-b625-30fd99755adc",
    "tid": "815282d5-9fa2-4fe7-baad-b229e79179ae"
}

SOME_DEVICE_ID = '79f48423-6403-4775-b76b-6eeb9dab7ea7WIN-TV9UBKLP1KN.TestSecDomain.test'

cylance_json_file_mock_credentials = {
    FILE_NAME: "CYLANCE_MOCK",
    USERS_DATA: FileForCredentialsMock(USERS_DATA, '''
    {
        "users" : [],
         "fields" : [],
         "additional_schema" : [],
         "raw_fields" : []                      
    }
    '''),
    DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, """
    {
    "devices": [{
        "accurate_for_datetime": "2019-03-01 18:21:51",
        "adapter_properties": [
            "Endpoint_Protection_Platform",
            "Agent",
            "Manager"
        ],
        "agent_version": "2.0.1490",
        "agent_versions": [{
            "adapter_name": "Cylance Agent",
            "agent_version": "2.0.1490",
            "agent_version_raw": "0000000020000000000001490"
        }],
        "connected_devices": [],
        "device_state": "Offline",
        "domain": "TestDomain.test",
        "fetch_time": "2020-09-08 01:40:48",
        "first_fetch_time": "2019-11-11 12:16:46",
        "hostname": "EC2AMAZ-V8E9DHF.TestDomain.test",
        "id": "2002948d-383b-410a-9c4e-e9e38794e08dEC2AMAZ-V8E9DHF.TestDomain.test",
        "is_safe": "True",
        "last_seen": "2019-03-16 17:58:23",
        "last_used_users": [
            "Administrator@TestDomain.test"
        ],
        "name":"EC2AMAZ-V8E9DHF",
        "network_interfaces": [{
            "ips": [
                "10.0.2.178"
            ],
            "ips_raw": [
                167772850
            ],
            "ips_v4": [
                "10.0.2.178"
            ],
            "ips_v4_raw": [
                167772850
            ],
            "mac": "06:DE:D4:0F:B4:18"
        }],
        "os": {
            "distribution": "Server 2016",
            "is_windows_server": true,
            "os_str": "microsoft windows server 2016 datacenter",
            "type": "Windows",
            "type_distribution": "Windows Server 2016"
        },
        "policies_details": [
            "auto_blocking:0","auto_uploading:0",
            "threat_report_limit:500",
            "low_confidence_threshold:-600",
            "full_disc_scan:0",
            "watch_for_new_files:0",
            "memory_exploit_detection:0",
            "trust_files_in_scan_exception_list:0",
            "logpolicy:0",
            "script_control:0",
            "prevent_service_shutdown:0",
            "scan_max_archive_size:0",
            "sample_copy_path:",
            "kill_running_threats:0",
            "show_notifications:0",
            "optics_set_disk_usage_maximum_fixed:1000",
            "optics_malware_auto_upload:0",
            "optics_memory_defense_auto_upload:0",
            "optics_script_control_auto_upload:0",
            "optics_application_control_auto_upload:0",
            "device_control:0",
            "optics:0",
            "auto_delete:0",
            "days_until_deleted:14",
            "pdf_auto_uploading:0",
            "ole_auto_uploading:0",
            "data_privacy:0",
            "docx_auto_uploading:0",
            "powershell_auto_uploading:0",
            "python_auto_uploading:0",
            "autoit_auto_uploading:0",
            "optics_show_notifications:0",
            "custom_thumbprint:",
            "scan_exception_list:[]",
            "optics_sensors_dns_visibility:0",
            "optics_sensors_private_network_address_visibility:0",
            "optics_sensors_windows_event_log_visibility:0",
            "optics_sensors_advanced_powershell_visibility:0",
            "optics_sensors_advanced_wmi_visibility:0",
            "optics_sensors_advanced_executable_parsing:0",
            "optics_sensors_enhanced_process_hooking_visibility:0",
            "optics_sensors_intel_cryptomining_detection:0"
        ],
        "policy_id": "00000000-0000-0000-0000-000000000000",
        "policy_name": "Default",
        "pretty_id": "AX-8",
        "plugin_name": "cylance_adapter",
        "plugin_type": "Adapter",
        "plugin_unique_name": "cylance_adapter_0",
        "quick_id": "cylance_adapter_0!2002948d-383b-410a-9c4e-e9e38794e08dEC2AMAZ-V8E9DHF.TestDomain.test",
        "type": "entitydata"
    }],
	"fields": [
	    "id",
	    "adapters",
	    "adapter_list_length",
	    "internal_axon_id",
	    "name",
        "hostname",
	    "last_seen",
	    "fetch_time",
	    "first_fetch_time",
	    "network_interfaces",
	    "network_interfaces.name",
	    "network_interfaces.mac",
	    "network_interfaces.manufacturer",
	    "network_interfaces.ips",
	    "os.type",
	    "os.distribution",
	    "os.is_windows_server",
	    "os.os_str",
	    "os.type_distribution",
	    "connected_devices",
	    "adapter_properties",
	    "policy_id",
	    "policy_name",
	    "policies_details",
	    "agent_version",
	    "agent_versions",
	    "agent_versions.adapter_name",
	    "agent_versions.agent_version",
	    "device_state",
	    "domain"
    ],
	"additional_schema": [{
	    "name": "is_safe",
	    "type": "string",
	    "title": "Is Safe"
    }, {
        "name": "device_state",
        "type": "string",
        "enum": [
            "Online", "Offline"
        ],
        "title": "Device State"
    }, {
        "name": "policy_id",
        "type": "string",
        "title": "Policy ID"
    }, {
        "name": "policy_name",
        "type": "string",
        "title": "Policy Name"
    }, {
	    "name": "policies_details",
	    "type": "array",
	    "items": {
	        "type": "string"
        },
        "title": "Policies Details"
	}, {
	    "name": "tenant_tag",
	    "type": "string",
	    "title": "Tenant Tag"
    }, {
        "name": "zone_names",
        "type": "array",
        "items": {
            "type": "string"
        },
        "title": "Zone Names"
    }, {
        "name": "agent_version",
        "type": "string",
        "title": "Cylance Agent Version"
    }],
	"raw_fields": []
}
    """)
}
