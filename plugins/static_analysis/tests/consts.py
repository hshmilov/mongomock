from bson import ObjectId
# from dateutil.parser import parse as ISODate

# pylint: disable=invalid-string-quote, line-too-long
VALID_SOFTWARE_LIST = [{'vendor_name': 'CrowdStrike, Inc.',
                        'product_name': 'CrowdStrike Device Control',
                        'product_version': '5.11.9255.0'},
                       {'vendor_name': 'IBM Corp.',
                        'product_name': 'IBM BigFix Client',
                        'product_version': '9.5.2.56'},
                       {'vendor_name': 'The Wireshark developer community, https://www.wireshark.org',
                        'product_name': 'Wireshark 2.4.6 32-bit',
                        'product_version': '2.4.6'},
                       {'vendor_name': 'Google LLC',
                        'product_name': 'Google Chrome',
                        'product_version': '75.0.3770.100'}]
INVALID_SOFTWARE_LIST = [{'vendor_name': '', 'product_name': '', 'product_version': ''},
                         {'vendor_name': '4', 'product_name': 'asdf', 'product_version': 'True'},
                         {'vendor_name': 'Google Chrome', 'product_name': 'Google LLC', 'product_version': '00'},
                         {'vendor_name': 'asdf', 'product_name': 'qwerty', 'product_version': 'hello world'}]
VALID_CVES_LIST = ['CVE-2016-2183', 'CVE-2019-0708', 'CVE-1999-1196', 'CVE-2014-1734']
INVALID_CVES_LIST = ['anna', 'CVE-1776-0704', '4.8', 'False']

ENTRY_SOFTWARE_CVES_ONLY = {
    "_id": ObjectId("5d34146d3ed16f0014397634"),
    "internal_axon_id": "96ed868be96b0af674b1b4e8bebdfaa3",
    "adapters": [
        {
            "client_used": "tenablesc.eastus.cloudapp.azure.com",
            "plugin_type": "Adapter",
            "plugin_name": "tenable_security_center_adapter",
            "plugin_unique_name": "tenable_security_center_adapter_0",
            "type": "entitydata",
            "data": {
                "os": {},
                "network_interfaces": [
                    {
                        "ips": [
                            "1.1.1.1"
                        ],
                        "ips_raw": [
                            16843009
                        ]
                    }
                ],
                "hostname": "one.one.one.one",
                "repository_name": "repo",
                "software_cves": [
                    {
                        "cve_id": "CVE-1999-0024"
                    },
                    {
                        "cve_id": "CVE-2006-0987"
                    },
                    {
                        "cve_id": "CVE-2016-2183"
                    }
                ],
                "id": "one.one.one.one__['1.1.1.1']",
                "raw": {
                    "ip": "1.1.1.1",
                    "uuid": "",
                    "score": "15",
                    "total": "32",
                    "severityInfo": "27",
                    "severityLow": "0",
                    "severityMedium": "5",
                    "severityHigh": "0",
                    "severityCritical": "0",
                    "macAddress": "",
                    "policyName": "1e2e4247-0de7-56d5-8026-34ab1f3150ef-1440143/test_9845771654157357",
                    "pluginSet": "201907192033",
                    "netbiosName": "",
                    "dnsName": "one.one.one.one",
                    "osCPE": "",
                    "biosGUID": "",
                    "tpmID": "",
                    "mcafeeGUID": "",
                    "lastAuthRun": "",
                    "lastUnauthRun": "1563651552",
                    "uniqueness": "repositoryID,ip,dnsName",
                    "repository": {
                        "id": "1",
                        "name": "repo",
                        "description": "",
                        "dataFormat": "IPv4"
                    },
                    "software": [],
                },
                "connected_devices": [],
                "scanner": True,
                "correlates": None,
                "adapter_properties": [
                    "Network",
                    "Vulnerability_Assessment"
                ],
                "installed_software": [],
                "pretty_id": "AX-2587"
            }
        }
    ],
    "tags": [
        {
            "association_type": "Tag",
            "associated_adapters": [
                [
                    "tenable_security_center_adapter_0",
                    "one.one.one.one__['1.1.1.1']"
                ]
            ],
            "name": "static_analysis_0",
            "data": {
                "id": "static_analysis_0!cve!96ed868be96b0af674b1b4e8bebdfaa3"
            },
            "type": "adapterdata",
            "entity": "devices",
            "action_if_exists": "update",
            "hidden_for_gui": True,
            "plugin_unique_name": "static_analysis_0",
            "plugin_name": "static_analysis",
            "associated_adapter_plugin_name": "tenable_security_center_adapter"
        }
    ],
    "adapter_list_length": 1
}

ENTRY_INSTALLED_SOFTWARE_ONLY = {
    "_id": ObjectId("5d3070aa8ac0c000c8b7a249"),
    "internal_axon_id": "49edf96483557bb4eff9ea547d9555bc",
    "adapters": [
        {
            "client_used": "tenablesc.eastus.cloudapp.azure.com",
            "plugin_type": "Adapter",
            "plugin_name": "tenable_security_center_adapter",
            "plugin_unique_name": "tenable_security_center_adapter_0",
            "type": "entitydata",
            "data": {
                "id": "bd77cf39-0a6d-4d87-a7cf-9e3876ea5525win-client.cymulate.test",
                "uuid": "bd77cf39-0a6d-4d87-a7cf-9e3876ea5525",
                "os": {},
                "network_interfaces": [
                    {
                        "ips": [
                            "10.132.0.6"
                        ],
                        "ips_raw": [
                            176422918
                        ]
                    }
                ],
                "hostname": "win-client.cymulate.test",
                "repository_name": "agent_repo",
                "score": 299,
                "total": 316,
                "severity_info": 290,
                "severity_low": 0,
                "severity_medium": 3,
                "severity_high": 21,
                "severity_critical": 2,
                "raw": {
                    "ip": "10.132.0.6",
                    "uuid": "bd77cf39-0a6d-4d87-a7cf-9e3876ea5525",
                    "score": "299",
                    "total": "316",
                    "severityInfo": "290",
                    "severityLow": "0",
                    "severityMedium": "3",
                    "severityHigh": "21",
                    "severityCritical": "2",
                    "macAddress": "",
                    "policyName": "",
                    "pluginSet": "",
                    "netbiosName": "",
                    "dnsName": "win-client.cymulate.test",
                    "osCPE": "cpe:/o:microsoft:windows_server_2008:r2:sp1:x64-datacenter",
                    "biosGUID": "",
                    "tpmID": "",
                    "mcafeeGUID": "",
                    "lastAuthRun": "1560359215",
                    "lastUnauthRun": "",
                    "uniqueness": "repositoryID,uuid",
                    "repository": {
                        "id": "3",
                        "name": "agent_repo",
                        "description": "",
                        "dataFormat": "agent"
                    },
                    "software": []
                },
                "connected_devices": [],
                "scanner": True,
                "correlates": None,
                "adapter_properties": [
                    "Network",
                    "Vulnerability_Assessment"
                ],
                "pretty_id": "AX-2397",
                "installed_software": [
                    {
                        "name": "AWS PV Drivers",
                        "vendor": "Amazon Web Services",
                        "version": "7.4.6"
                    },
                    {
                        "name": "CrowdStrike Device Control",
                        "vendor": "CrowdStrike, Inc.",
                        "version": "5.11.9255.0"
                    },
                    {
                        "name": "EC2ConfigService",
                        "vendor": "Amazon Web Services",
                        "version": "4.9.2188.0"
                    },
                    {
                        "name": "Google Chrome",
                        "vendor": "Google LLC",
                        "version": "75.0.3770.142"
                    },
                    {
                        "name": "Sophos Endpoint",
                        "vendor": "1.5.12",
                        "version": "Sophos Limited"
                    },
                    {
                        "name": "Adobe Flash Player 30 PPAPI",
                        "vendor": "Adobe Systems Incorporated",
                        "version": "30.0.0.113"
                    },
                    {
                        "name": "Safari",
                        "version": "11.1.2"
                    },
                    {
                        "name": "Wireshark 2.4.0 64-bit",
                        "vendor": "The Wireshark developer community, https://www.wireshark.org",
                        "version": "2.4.0"
                    }
                ]
            }
        }
    ],
    "tags": [
        {
            "association_type": "Tag",
            "associated_adapters": [
                [
                    "tenable_security_center_adapter_0",
                    "bd77cf39-0a6d-4d87-a7cf-9e3876ea5525win-client.cymulate.test"
                ]
            ],
            "name": "static_analysis_0",
            "data": {
                "id": "static_analysis_0!cve!49edf96483557bb4eff9ea547d9555bc"
            },
            "type": "adapterdata",
            "entity": "devices",
            "action_if_exists": "update",
            "hidden_for_gui": True,
            "plugin_unique_name": "static_analysis_0",
            "plugin_name": "static_analysis",
            "associated_adapter_plugin_name": "tenable_security_center_adapter"
        }
    ],
    "adapter_list_length": 1
}

ENTRY_NEITHER_CVES_NOR_SOFTWARE = {
    "_id": ObjectId("5d2d7c1c7d43550015e9a6b1"),
    "internal_axon_id": "265b64df90a622f79d4c8e01288cb3c3",
    "adapters": [
        {
            "client_used": "192.168.10.1:443",
            "plugin_type": "Adapter",
            "plugin_name": "fortigate_adapter",
            "plugin_unique_name": "fortigate_adapter_0",
            "type": "entitydata",
            "data": {
                "hostname": "dc4",
                "fortigate_name": "192.168.10.1:443",
                "id": "fortigate_192.168.10.1:443_00:0C:29:B6:DA:46_dc4",
                "network_interfaces": [
                    {
                        "mac": "00:0C:29:B6:DA:46",
                        "manufacturer": "VMware, Inc. (3401 Hillview Avenue Palo Alto CA US 94304 )",
                        "ips": [
                            "192.168.20.17"
                        ],
                        "ips_raw": [
                            3232240657
                        ]
                    }
                ],
                "interface": "ESX",
                "raw": {
                    "ip": "192.168.20.17",
                    "mac": "00:0c:29:b6:da:46",
                    "vci": "MSFT 5.0",
                    "hostname": "dc4",
                    "expire": "Wed Jul 24 22:32:09 2019",
                    "expire_time": 1563996729,
                    "status": "leased",
                    "interface": "ESX",
                    "type": "ipv4",
                    "reserved": True,
                    "fortios_name": "192.168.10.1:443"
                },
                "connected_devices": [],
                "adapter_properties": [
                    "Network",
                    "Firewall"
                ],
                "pretty_id": "AX-1722"
            }
        },
        {
            "client_used": "192.168.20.10",
            "plugin_type": "Adapter",
            "plugin_name": "nexpose_adapter",
            "plugin_unique_name": "nexpose_adapter_0",
            "type": "entitydata",
            "data": {
                "os": {
                    "type": "Windows",
                    "distribution": "Server 2012"
                },
                "id": "9DC4",
                "network_interfaces": [
                    {
                        "mac": "00:0C:29:B6:DA:46",
                        "manufacturer": "VMware, Inc. (3401 Hillview Avenue Palo Alto CA US 94304 )",
                        "ips": [
                            "192.168.20.17"
                        ],
                        "ips_raw": [
                            3232240657
                        ]
                    }
                ],
                "hostname": "DC4",
                "risk_score": 8507.10546875,
                "vulnerabilities_critical": 2,
                "vulnerabilities_exploits": 12,
                "vulnerabilities_malwareKits": 1,
                "vulnerabilities_moderate": 7,
                "vulnerabilities_severe": 11,
                "vulnerabilities_total": 20,
                "raw": {
                    "addresses": [
                        {
                            "ip": "192.168.20.17",
                            "mac": "00:0C:29:B6:DA:46"
                        }
                    ],
                    "assessedForPolicies": False,
                    "assessedForVulnerabilities": True,
                    "hostName": "DC4",
                    "hostNames": [
                        {
                            "name": "DC4",
                            "source": "netbios"
                        },
                        {
                            "name": "dc4.TestDomain.test",
                            "source": "ldap"
                        }
                    ],
                    "id": 9,
                    "ip": "192.168.20.17",
                    "mac": "00:0C:29:B6:DA:46",
                    "os": "Microsoft Windows Server 2012 R2 Standard Edition",
                    "osFingerprint": {
                        "cpe": {
                            "edition": "-",
                            "part": "o",
                            "product": "windows_server_2012",
                            "swEdition": "standard",
                            "update": "-",
                            "v2_DOT__DOT_2": "cpe:/o:microsoft:windows_server_2012:r2:-:~-~standard~~~",
                            "v2_DOT__DOT_3": "cpe:2.3:o:microsoft:windows_server_2012:r2:-:-:*:standard:*:*:*",
                            "vendor": "microsoft",
                            "version": "r2"
                        },
                        "description": "Microsoft Windows Server 2012 R2 Standard Edition",
                        "family": "Windows",
                        "id": 74,
                        "product": "Windows Server 2012 R2 Standard Edition",
                        "systemName": "Microsoft Windows",
                        "type": "General",
                        "vendor": "Microsoft"
                    },
                    "rawRiskScore": 8507.10546875,
                    "riskScore": 8507.10546875,
                    "vulnerabilities": {
                        "critical": 2,
                        "exploits": 12,
                        "malwareKits": 1,
                        "moderate": 7,
                        "severe": 11,
                        "total": 20
                    },
                    "API": "3",
                    "tags": [],
                    "software": []
                },
                "connected_devices": [],
                "scanner": True,
                "correlates": [
                    "fortigate_adapter_0",
                    "fortigate_192.168.10.1:443_00:0C:29:B6:DA:46_dc4"
                ],
                "adapter_properties": [
                    "Network",
                    "Vulnerability_Assessment"
                ],
                "pretty_id": "AX-2558"
            }
        }
    ],
    "tags": [],
    "adapter_list_length": 2
}

ENTRY_BOTH_CVES_AND_SOFTWARE = {
    "_id": ObjectId("5d3070988ac0c000c8b7a1c0"),
    "internal_axon_id": "48a4829422366cb08a4f2966ae6419cb",
    "adapters": [
        {
            "client_used": "tenablesc.eastus.cloudapp.azure.com",
            "plugin_type": "Adapter",
            "plugin_name": "tenable_security_center_adapter",
            "plugin_unique_name": "tenable_security_center_adapter_0",
            "type": "entitydata",
            "data": {
                "id": "64b63d58-b7ec-4bfe-ab36-7fc369501569localhost",
                "uuid": "64b63d58-b7ec-4bfe-ab36-7fc369501569",
                "os": {},
                "network_interfaces": [
                    {
                        "mac": "00:0D:3A:19:2F:4B",
                        "manufacturer": "Microsoft Corp. (One Microsoft Way Redmond Wa. US 98052 )",
                        "ips": [
                            "127.0.0.1"
                        ],
                        "ips_raw": [
                            2130706433
                        ]
                    }
                ],
                "hostname": "localhost",
                "repository_name": "repo",
                "score": 99,
                "total": 113,
                "severity_info": 95,
                "severity_low": 2,
                "severity_medium": 9,
                "severity_high": 7,
                "severity_critical": 0,
                "policy_name": "1e2e4247-0de7-56d5-8026-34ab1f3150ef-1439866/Basic Network Scan",
                "software_cves": [
                    {
                        "cve_id": "CVE-2008-5161"
                    },
                    {
                        "cve_id": "CVE-2019-6454"
                    },
                    {
                        "cve_id": "CVE-2019-6133"
                    },
                    {
                        "cve_id": "CVE-2018-5407"
                    },
                    {
                        "cve_id": "CVE-2018-17972"
                    },
                    {
                        "cve_id": "CVE-2018-18445"
                    },
                    {
                        "cve_id": "CVE-2018-9568"
                    },
                    {
                        "cve_id": "CVE-2019-1559"
                    },
                    {
                        "cve_id": "CVE-2017-18214"
                    },
                    {
                        "cve_id": "CVE-2016-4055"
                    },
                    {
                        "cve_id": "CVE-2019-3855"
                    },
                    {
                        "cve_id": "CVE-2019-3856"
                    },
                    {
                        "cve_id": "CVE-2019-3857"
                    },
                    {
                        "cve_id": "CVE-2019-3863"
                    }
                ],
                "raw": {
                    "ip": "127.0.0.1",
                    "uuid": "64b63d58-b7ec-4bfe-ab36-7fc369501569",
                    "score": "99",
                    "total": "113",
                    "severityInfo": "95",
                    "severityLow": "2",
                    "severityMedium": "9",
                    "severityHigh": "7",
                    "severityCritical": "0",
                    "macAddress": "00:0d:3a:19:2f:4b",
                    "policyName": "1e2e4247-0de7-56d5-8026-34ab1f3150ef-1439866/Basic Network Scan",
                    "pluginSet": "201907192033",
                    "netbiosName": "UNKNOWN\\nessus7",
                    "dnsName": "localhost",
                    "osCPE": "cpe:/o:centos:centos:7:update6",
                    "biosGUID": "05f82415-7099-114e-824e-ae630d2c5bad",
                    "tpmID": "",
                    "mcafeeGUID": "",
                    "lastAuthRun": "1563638671",
                    "lastUnauthRun": "1563158650",
                    "uniqueness": "repositoryID,ip,dnsName",
                    "repository": {
                        "id": "1",
                        "name": "repo",
                        "description": "",
                        "dataFormat": "IPv4"
                    },
                    "software": []
                },
                "connected_devices": [],
                "scanner": True,
                "correlates": None,
                "adapter_properties": [
                    "Network",
                    "Vulnerability_Assessment"
                ],
                "pretty_id": "AX-2386",
                "installed_software": [
                    {
                        "name": "AWS Tools for Windows",
                        "vendor": "Amazon Web Services Developer Relations",
                        "version": "3.15.172"
                    },
                    {
                        "name": "Google Chrome",
                        "vendor": "Google LLC",
                        "version": "75.0.3770.142"
                    },
                    {
                        "name": "IBM BigFix Client",
                        "vendor": "IBM Corp.",
                        "version": "9.5.2.56"
                    },

                    {
                        "name": "VMware Tools",
                        "version": "10.1.7.5541682",
                        "vendor": "VMware, Inc."
                    },
                    {
                        "name": "SQL Server 2012 Common Files",
                        "version": "11.0.2100.60",
                        "vendor": "Microsoft Corporation"
                    },
                    {
                        "name": "Adobe Flash Player 30 PPAPI",
                        "vendor": "Adobe Systems Incorporated",
                        "version": "30.0.0.113"
                    },
                    {
                        "name": "Safari",
                        "version": "11.1.2"
                    }
                ]
            }
        }
    ],
    "tags": [
        {
            "association_type": "Tag",
            "associated_adapters": [
                [
                    "tenable_security_center_adapter_0",
                    "64b63d58-b7ec-4bfe-ab36-7fc369501569localhost"
                ]
            ],
            "name": "static_analysis_0",
            "data": {
                "id": "static_analysis_0!cve!48a4829422366cb08a4f2966ae6419cb"
            },
            "type": "adapterdata",
            "entity": "devices",
            "action_if_exists": "update",
            "hidden_for_gui": True,
            "plugin_unique_name": "static_analysis_0",
            "plugin_name": "static_analysis",
            "associated_adapter_plugin_name": "tenable_security_center_adapter"
        }
    ],
    "adapter_list_length": 1
}


ENTRY_WITH_TWO_ADAPTERS_CORRELATED = {
    "_id": ObjectId("5d2d7c1c7d43550015e9a6b6"),
    "internal_axon_id": "6d57a77610898b91f8da33b80d52e517",
    "adapters": [
        {
            "client_used": "192.168.10.1:443",
            "plugin_type": "Adapter",
            "plugin_name": "fortigate_adapter",
            "plugin_unique_name": "fortigate_adapter_0",
            "type": "entitydata",
            "data": {
                "hostname": "cisco-emulator",
                "fortigate_name": "192.168.10.1:443",
                "id": "fortigate_192.168.10.1:443_00:50:56:91:4F:24_cisco-emulator",
                "network_interfaces": [
                    {
                        "mac": "00:50:56:91:4F:24",
                        "manufacturer": "VMware, Inc. (3401 Hillview Avenue PALO ALTO CA US 94304 )",
                        "ips": [
                            "192.168.20.21"
                        ],
                        "ips_raw": [
                            3232240661
                        ]
                    }
                ],
                "interface": "ESX",
                "raw": {
                    "ip": "192.168.20.21",
                    "mac": "00:50:56:91:4f:24",
                    "hostname": "cisco-emulator",
                    "expire": "Fri Jul 26 13:15:35 2019",
                    "expire_time": 1564136135,
                    "status": "leased",
                    "interface": "ESX",
                    "type": "ipv4",
                    "reserved": True,
                    "fortios_name": "192.168.10.1:443"
                },
                "software_cves": [
                    {"cve_id": "CVE-2019-5789"},
                    {"cve_id": "CVE-2005-2028"},
                    {"cve_id": "CVE-2018-20014"}
                ],
                "connected_devices": [],
                "adapter_properties": [
                    "Network",
                    "Firewall"
                ],
                "pretty_id": "AX-1733"
            }
        },
        {
            "client_used": "192.168.20.10",
            "plugin_type": "Adapter",
            "plugin_name": "nexpose_adapter",
            "plugin_unique_name": "nexpose_adapter_0",
            "type": "entitydata",
            "data": {
                "os": {
                    "type": "Linux",
                    "distribution": "Ubuntu"
                },
                "id": "18",
                "installed_software": [
                    {
                        "name": "Wireshark 2.4.0 64-bit",
                        "vendor": "The Wireshark developer community, https://www.wireshark.org",
                        "version": "2.4.0"
                    },
                    {
                        "name": "Adobe Flash Player 30 PPAPI",
                        "vendor": "Adobe Systems Incorporated",
                        "version": "30.0.0.113"
                    },
                    {
                        "name": "Safari",
                        "version": "11.1.2"
                    }
                ],
                "network_interfaces": [
                    {
                        "mac": "00:50:56:91:4F:24",
                        "manufacturer": "VMware, Inc. (3401 Hillview Avenue PALO ALTO CA US 94304 )",
                        "ips": [
                            "192.168.20.21"
                        ],
                        "ips_raw": [
                            3232240661
                        ]
                    }
                ],
                "raw": {
                    "addresses": [
                        {
                            "ip": "192.168.20.21",
                            "mac": "00:50:56:91:4F:24"
                        }
                    ],
                    "assessedForPolicies": False,
                    "assessedForVulnerabilities": True,
                    "id": 18,
                    "ip": "192.168.20.21",
                    "mac": "00:50:56:91:4F:24",
                    "os": "Ubuntu Linux",
                    "osFingerprint": {
                        "description": "Ubuntu Linux",
                        "family": "Linux",
                        "id": 1,
                        "product": "Linux",
                        "systemName": "Ubuntu Linux",
                        "type": "General",
                        "vendor": "Ubuntu"
                    },
                    "rawRiskScore": 0.0,
                    "riskScore": 0.0,
                    "vulnerabilities": {
                        "critical": 0,
                        "exploits": 0,
                        "malwareKits": 0,
                        "moderate": 2,
                        "severe": 0,
                        "total": 2
                    },
                    "API": "3",
                    "tags": [],
                    "software": []
                },
                "connected_devices": [],
                "scanner": True,
                "correlates": [
                    "fortigate_adapter_0",
                    "fortigate_192.168.10.1:443_00:50:56:91:4F:24_cisco-emulator"
                ],
                "adapter_properties": [
                    "Network",
                    "Vulnerability_Assessment"
                ],
                "pretty_id": "AX-2551"
            }
        }
    ],
    "tags": [],
    "adapter_list_length": 2
}

ENTRY_WITH_ADAPTER_REMOVED_AND_NO_CVES = {
    "_id": ObjectId("5d305f5c0c067c00c982bce3"),
    "internal_axon_id": "7aceabfac01561d2fc23c1b9b1433931",
    "adapters": [
        {
            "client_used": "192.168.10.1:443",
            "plugin_type": "Adapter",
            "plugin_name": "fortigate_adapter",
            "plugin_unique_name": "fortigate_adapter_0",
            "type": "entitydata",
            "data": {
                "hostname": "cisco-emulator",
                "fortigate_name": "192.168.10.1:443",
                "id": "fortigate_192.168.10.1:443_00:50:56:91:4F:24_cisco-emulator",
                "network_interfaces": [
                    {
                        "mac": "00:50:56:91:4F:24",
                        "manufacturer": "VMware, Inc. (3401 Hillview Avenue PALO ALTO CA US 94304 )",
                        "ips": [
                            "192.168.20.21"
                        ],
                        "ips_raw": [
                            3232240661
                        ]
                    }
                ],
                "interface": "ESX",
                "raw": {
                    "ip": "192.168.20.21",
                    "mac": "00:50:56:91:4f:24",
                    "hostname": "cisco-emulator",
                    "expire": "Fri Jul 26 13:15:35 2019",
                    "expire_time": 1564136135,
                    "status": "leased",
                    "interface": "ESX",
                    "type": "ipv4",
                    "reserved": True,
                    "fortios_name": "192.168.10.1:443"
                },
                "connected_devices": [],
                "adapter_properties": [
                    "Network",
                    "Firewall"
                ],
                "pretty_id": "AX-1733"
            }
        },
    ],
    "tags": [
        {
            "association_type": "Tag",
            "associated_adapters": [
                [
                    "tenable_security_center_adapter_0",
                    "kb.logrhythm.com__['65.127.112.131']"
                ]
            ],
            "name": "static_analysis_0",
            "data": {
                "id": "static_analysis_0!cve!e47c3b4b522c033bf113ed632ce4b563",
                "software_cves": [
                    {
                        "cvss": 7.5,
                        "cve_id": "CVE-2016-2183",
                        "cve_description": "The DES and Triple DES ciphers, as used in the TLS, SSH, and IPSec protocols and other protocols and products, have a birthday bound of approximately four billion blocks, which makes it easier for remote attackers to obtain cleartext data via a birthday attack against a long-duration encrypted session, as demonstrated by an HTTPS session using Triple DES in CBC mode, aka a \"Sweet32\" attack.",
                        "cve_references": [
                            "http://kb.juniper.net/InfoCenter/index?page=content&id=JSA10759",
                            "http://lists.opensuse.org/opensuse-security-announce/2016-10/msg00013.html",
                            "https://security.gentoo.org/glsa/201707-01",
                            "https://security.netapp.com/advisory/ntap-20160915-0001/",
                            "https://security.netapp.com/advisory/ntap-20170119-0001/",
                            "https://sweet32.info/",
                            "https://www.ietf.org/mail-archive/web/tls/current/msg04560.html",
                            "https://www.mitel.com/en-ca/support/security-advisories/mitel-product-security-advisory-17-0008",
                            "https://www.nccgroup.trust/us/about-us/newsroom-and-events/blog/2016/august/new-practical-attacks-on-64-bit-block-ciphers-3des-blowfish/",
                            "https://www.openssl.org/blog/blog/2016/08/24/sweet32/",
                            "https://www.sigsac.org/ccs/CCS2016/accepted-papers/",
                            "https://www.tenable.com/security/tns-2016-16",
                            "https://www.tenable.com/security/tns-2016-20",
                            "https://www.tenable.com/security/tns-2016-21",
                            "https://www.tenable.com/security/tns-2017-09",
                            "https://www.teskalabs.com/blog/teskalabs-bulletin-160826-seacat-sweet32-issue"
                        ],
                        "cve_severity": "HIGH",
                        "software_name": "content_security_management_appliance",
                        "software_vendor": "cisco"
                    },
                    {
                        "cvss": 5.9,
                        "cve_id": "CVE-2013-2566",
                        "cve_description": "The RC4 algorithm, as used in the TLS protocol and SSL protocol, has many single-byte biases, which makes it easier for remote attackers to conduct plaintext-recovery attacks via statistical analysis of ciphertext in a large number of sessions that use the same plaintext.",
                        "cve_references": [
                            "http://blog.cryptographyengineering.com/2013/03/attack-of-week-rc4-is-kind-of-broken-in.html",
                            "http://cr.yp.to/talks/2013.03.12/slides.pdf",
                            "http://kb.juniper.net/InfoCenter/index?page=content&id=JSA10705",
                            "http://marc.info/?l=bugtraq&m=143039468003789&w=2",
                            "http://my.opera.com/securitygroup/blog/2013/03/20/on-the-precariousness-of-rc4",
                            "http://security.gentoo.org/glsa/glsa-201406-19.xml",
                            "http://www.isg.rhul.ac.uk/tls/",
                            "http://www.mozilla.org/security/announce/2013/mfsa2013-103.html",
                            "http://www.opera.com/docs/changelogs/unified/1215/",
                            "http://www.opera.com/security/advisory/1046",
                            "http://www.oracle.com/technetwork/security-advisory/cpuapr2016v3-2985753.html",
                            "http://www.oracle.com/technetwork/security-advisory/cpujan2018-3236628.html",
                            "http://www.oracle.com/technetwork/security-advisory/cpujul2016-2881720.html",
                            "http://www.oracle.com/technetwork/security-advisory/cpuoct2016-2881722.html",
                            "http://www.oracle.com/technetwork/security-advisory/cpuoct2017-3236626.html",
                            "http://www.securityfocus.com/bid/58796",
                            "http://www.ubuntu.com/usn/USN-2031-1",
                            "http://www.ubuntu.com/usn/USN-2032-1",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05289935",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05336888",
                            "https://security.gentoo.org/glsa/201504-01"
                        ],
                        "cve_severity": "MEDIUM",
                        "software_name": "safari",
                        "software_vendor": "apple"
                    },
                    {
                        "cvss": 4.3,
                        "cve_id": "CVE-2015-2808",
                        "cve_description": "The RC4 algorithm, as used in the TLS protocol and SSL protocol, does not properly combine state data with key data during the initialization phase, which makes it easier for remote attackers to conduct plaintext-recovery attacks against the initial bytes of a stream by sniffing network traffic that occasionally relies on keys affected by the Invariance Weakness, and then using a brute-force approach involving LSB values, aka the \"Bar Mitzvah\" issue.",
                        "cve_references": [
                            "http://h20564.www2.hpe.com/hpsc/doc/public/display?docId=emr_na-c04779034",
                            "http://kb.juniper.net/InfoCenter/index?page=content&id=JSA10705",
                            "http://kb.juniper.net/InfoCenter/index?page=content&id=JSA10727",
                            "http://lists.opensuse.org/opensuse-security-announce/2015-06/msg00013.html",
                            "http://lists.opensuse.org/opensuse-security-announce/2015-06/msg00014.html",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05085988",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05193347",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05289935",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05336888",
                            "https://kb.juniper.net/JSA10783",
                            "https://kc.mcafee.com/corporate/index?page=content&id=SB10163",
                            "https://security.gentoo.org/glsa/201512-10",
                            "https://www.blackhat.com/docs/asia-15/materials/asia-15-Mantin-Bar-Mitzvah-Attack-Breaking-SSL-With-13-Year-Old-RC4-Weakness-wp.pdf",
                            "https://www-947.ibm.com/support/entry/portal/docdisplay?lndocid=MIGR-5098709"
                        ],
                        "cve_severity": "MEDIUM",
                        "software_name": "safari",
                        "software_vendor": "apple"
                    }
                ]
            },
            "type": "adapterdata",
            "entity": "devices",
            "action_if_exists": "update",
            "hidden_for_gui": True,
            "plugin_unique_name": "static_analysis_0",
            "plugin_name": "static_analysis",
            "associated_adapter_plugin_name": "tenable_security_center_adapter"
        }
    ],
    "adapter_list_length": 1
}

ENTRY_WITH_ADAPTER_REMOVED_AND_DIFFERENT_CVES = {
    "_id": ObjectId("5d36bd37f6f0c100148c586c"),
    "internal_axon_id": "6fb1c3ae49b3e866b0e1fa078e6911db",
    "adapters": [
        {
            "client_used": "192.168.10.1:443",
            "plugin_type": "Adapter",
            "plugin_name": "fortigate_adapter",
            "plugin_unique_name": "fortigate_adapter_0",
            "type": "entitydata",
            "data": {
                "hostname": "cisco-emulator",
                "fortigate_name": "192.168.10.1:443",
                "id": "fortigate_192.168.10.1:443_00:50:56:91:4F:24_cisco-emulator",
                "network_interfaces": [
                    {
                        "mac": "00:50:56:91:4F:24",
                        "manufacturer": "VMware, Inc. (3401 Hillview Avenue PALO ALTO CA US 94304 )",
                        "ips": [
                            "192.168.20.21"
                        ],
                        "ips_raw": [
                            3232240661
                        ]
                    }
                ],
                "interface": "ESX",
                "raw": {
                    "ip": "192.168.20.21",
                    "mac": "00:50:56:91:4f:24",
                    "hostname": "cisco-emulator",
                    "expire": "Fri Jul 26 13:15:35 2019",
                    "expire_time": 1564136135,
                    "status": "leased",
                    "interface": "ESX",
                    "type": "ipv4",
                    "reserved": True,
                    "fortios_name": "192.168.10.1:443"
                },
                "software_cves": [
                    {"cve_id": "CVE-2019-5789"},
                    {"cve_id": "CVE-2005-2028"},
                    {"cve_id": "CVE-2018-20014"}
                ],
                "connected_devices": [],
                "adapter_properties": [
                    "Network",
                    "Firewall"
                ],
                "pretty_id": "AX-1733"
            }
        },
    ],
    "tags": [
        {
            "association_type": "Tag",
            "associated_adapters": [
                [
                    "tenable_security_center_adapter_0",
                    "kb.logrhythm.com__['65.127.112.131']"
                ]
            ],
            "name": "static_analysis_0",
            "data": {
                "id": "static_analysis_0!cve!e47c3b4b522c033bf113ed632ce4b563",
                "software_cves": [
                    {
                        "cvss": 7.5,
                        "cve_id": "CVE-2016-2183",
                        "cve_description": "The DES and Triple DES ciphers, as used in the TLS, SSH, and IPSec protocols and other protocols and products, have a birthday bound of approximately four billion blocks, which makes it easier for remote attackers to obtain cleartext data via a birthday attack against a long-duration encrypted session, as demonstrated by an HTTPS session using Triple DES in CBC mode, aka a \"Sweet32\" attack.",
                        "cve_references": [
                            "http://kb.juniper.net/InfoCenter/index?page=content&id=JSA10759",
                            "http://lists.opensuse.org/opensuse-security-announce/2016-10/msg00013.html",
                            "https://security.gentoo.org/glsa/201707-01",
                            "https://security.netapp.com/advisory/ntap-20160915-0001/",
                            "https://security.netapp.com/advisory/ntap-20170119-0001/",
                            "https://sweet32.info/",
                            "https://www.ietf.org/mail-archive/web/tls/current/msg04560.html",
                            "https://www.mitel.com/en-ca/support/security-advisories/mitel-product-security-advisory-17-0008",
                            "https://www.nccgroup.trust/us/about-us/newsroom-and-events/blog/2016/august/new-practical-attacks-on-64-bit-block-ciphers-3des-blowfish/",
                            "https://www.openssl.org/blog/blog/2016/08/24/sweet32/",
                            "https://www.sigsac.org/ccs/CCS2016/accepted-papers/",
                            "https://www.tenable.com/security/tns-2016-16",
                            "https://www.tenable.com/security/tns-2016-20",
                            "https://www.tenable.com/security/tns-2016-21",
                            "https://www.tenable.com/security/tns-2017-09",
                            "https://www.teskalabs.com/blog/teskalabs-bulletin-160826-seacat-sweet32-issue"
                        ],
                        "cve_severity": "HIGH",
                        "software_name": "content_security_management_appliance",
                        "software_vendor": "cisco"
                    },
                    {
                        "cvss": 5.9,
                        "cve_id": "CVE-2013-2566",
                        "cve_description": "The RC4 algorithm, as used in the TLS protocol and SSL protocol, has many single-byte biases, which makes it easier for remote attackers to conduct plaintext-recovery attacks via statistical analysis of ciphertext in a large number of sessions that use the same plaintext.",
                        "cve_references": [
                            "http://blog.cryptographyengineering.com/2013/03/attack-of-week-rc4-is-kind-of-broken-in.html",
                            "http://cr.yp.to/talks/2013.03.12/slides.pdf",
                            "http://kb.juniper.net/InfoCenter/index?page=content&id=JSA10705",
                            "http://marc.info/?l=bugtraq&m=143039468003789&w=2",
                            "http://my.opera.com/securitygroup/blog/2013/03/20/on-the-precariousness-of-rc4",
                            "http://security.gentoo.org/glsa/glsa-201406-19.xml",
                            "http://www.isg.rhul.ac.uk/tls/",
                            "http://www.mozilla.org/security/announce/2013/mfsa2013-103.html",
                            "http://www.opera.com/docs/changelogs/unified/1215/",
                            "http://www.opera.com/security/advisory/1046",
                            "http://www.oracle.com/technetwork/security-advisory/cpuapr2016v3-2985753.html",
                            "http://www.oracle.com/technetwork/security-advisory/cpujan2018-3236628.html",
                            "http://www.oracle.com/technetwork/security-advisory/cpujul2016-2881720.html",
                            "http://www.oracle.com/technetwork/security-advisory/cpuoct2016-2881722.html",
                            "http://www.oracle.com/technetwork/security-advisory/cpuoct2017-3236626.html",
                            "http://www.securityfocus.com/bid/58796",
                            "http://www.ubuntu.com/usn/USN-2031-1",
                            "http://www.ubuntu.com/usn/USN-2032-1",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05289935",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05336888",
                            "https://security.gentoo.org/glsa/201504-01"
                        ],
                        "cve_severity": "MEDIUM",
                        "software_name": "safari",
                        "software_vendor": "apple"
                    },
                    {
                        "cvss": 4.3,
                        "cve_id": "CVE-2015-2808",
                        "cve_description": "The RC4 algorithm, as used in the TLS protocol and SSL protocol, does not properly combine state data with key data during the initialization phase, which makes it easier for remote attackers to conduct plaintext-recovery attacks against the initial bytes of a stream by sniffing network traffic that occasionally relies on keys affected by the Invariance Weakness, and then using a brute-force approach involving LSB values, aka the \"Bar Mitzvah\" issue.",
                        "cve_references": [
                            "http://h20564.www2.hpe.com/hpsc/doc/public/display?docId=emr_na-c04779034",
                            "http://kb.juniper.net/InfoCenter/index?page=content&id=JSA10705",
                            "http://kb.juniper.net/InfoCenter/index?page=content&id=JSA10727",
                            "http://lists.opensuse.org/opensuse-security-announce/2015-06/msg00013.html",
                            "http://lists.opensuse.org/opensuse-security-announce/2015-06/msg00014.html",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05085988",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05193347",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05289935",
                            "https://h20566.www2.hpe.com/portal/site/hpsc/public/kb/docDisplay?docId=emr_na-c05336888",
                            "https://kb.juniper.net/JSA10783",
                            "https://kc.mcafee.com/corporate/index?page=content&id=SB10163",
                            "https://security.gentoo.org/glsa/201512-10",
                            "https://www.blackhat.com/docs/asia-15/materials/asia-15-Mantin-Bar-Mitzvah-Attack-Breaking-SSL-With-13-Year-Old-RC4-Weakness-wp.pdf",
                            "https://www-947.ibm.com/support/entry/portal/docdisplay?lndocid=MIGR-5098709"
                        ],
                        "cve_severity": "MEDIUM",
                        "software_name": "safari",
                        "software_vendor": "apple"
                    }
                ]
            },
            "type": "adapterdata",
            "entity": "devices",
            "action_if_exists": "update",
            "hidden_for_gui": True,
            "plugin_unique_name": "static_analysis_0",
            "plugin_name": "static_analysis",
            "associated_adapter_plugin_name": "tenable_security_center_adapter"
        }
    ],
    "adapter_list_length": 1
}
# pylint: enable=invalid-string-quote, line-too-long
