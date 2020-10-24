client_details = {
    'Kaseya_Domain': 'PREVIEW6.KASEYA.NET',
    'username': 'jakeg@axonius.com',
    'password': 'Jake0!',
    'verify_ssl': True
}

SOME_DEVICE_ID = '41731352988141242425148718_WIN-D14VSGS3C0G'

KASEYA_DB_MOCK_WITH_VULNERABILITES = [
    {
        'internal_axon_id': 'bd26c1d5e0fe413409a11940d899ecb3',
        'accurate_for_datetime': '2020-10-20T10:05:40.545Z',
        'adapters': [
            {
                'client_used': 'PREVIEW6.KASEYA.NET',
                'plugin_type': 'Adapter',
                'plugin_name': 'kaseya_adapter',
                'plugin_unique_name': 'kaseya_adapter_0',
                'type': 'entitydata',
                'accurate_for_datetime': '2020-10-20T09:59:18.293Z',
                'data': {
                    'id': '62138662552116244175452193_EC2AMAZ-V8E9DHF',
                    'name': 'ec2amaz-v8e9dhf.base.myOrg',
                    'os': {
                        'type': 'Windows',
                        'distribution': 'Server 2016',
                        'bitness': 64,
                        'os_str': 'windows 2016 server datacenter x64 edition  build 14393',
                        'is_windows_server': True,
                        'type_distribution': 'Windows Server 2016'
                    },
                    'hostname': 'EC2AMAZ-V8E9DHF',
                    'last_seen': '2020-10-13T10:14:50.747Z',
                    'time_zone': 'UTC',
                    'total_physical_memory': 32.0,
                    'device_manufacturer': 'Xen',
                    'network_interfaces': [
                        {
                            'mac': '06:DE:D4:0F:B4:18',
                            'ips': [
                                '10.0.2.178'
                            ],
                            'ips_v4': [
                                '10.0.2.178'
                            ],
                            'ips_v4_raw': [
                                167772850
                            ],
                            'ips_raw': [
                                167772850
                            ]
                        }
                    ],
                    'agent_id': '223798342126899',
                    'installed_software': [
                        {
                            'version_raw': '000000006000000070000000500000177',
                            'name_version': 'Cloud Workload Protection-6.7.5.177',
                            'name': 'Cloud Workload Protection',
                            'version': '6.7.5.177',
                            'vendor': 'Symantec',
                            'description': 'Setup Launcher Unicode',
                            'path': 'C:\\Users\\Administrator\\Desktop\\agent.exe'
                        }],
                    'agent_versions': [
                        {
                            'adapter_name': 'Kaseya Agent',
                            'agent_version': '9050012'
                        }
                    ],
                    'domain': 'TESTDOMAIN',
                    'connected_devices': [],
                    'fetch_time': '2020-10-20T09:59:17.497Z',
                    'adapter_properties': [
                        'Agent',
                        'Manager'
                    ],
                    'accurate_for_datetime': '2020-10-20T09:59:18.293Z',
                    'first_fetch_time': '2020-10-20T09:59:17.497Z',
                    'pretty_id': 'AX-0'
                },
                'quick_id': 'kaseya_adapter_0!62138662552116244175452193_EC2AMAZ-V8E9DHF'
            }
        ],
        'tags': [
            {
                'association_type': 'Tag',
                'associated_adapters': [
                    [
                        'kaseya_adapter_0',
                        '62138662552116244175452193_EC2AMAZ-V8E9DHF'
                    ]
                ],
                'name': 'static_analysis_0',
                'data': {
                    'id': 'static_analysis_0!cve!bd26c1d5e0fe413409a11940d899ecb3',
                    'software_cves': [
                        {
                            'cvss_str': 'CVSS 7.2',
                            'cvss': 7.2,
                            'cve_id': 'CVE-2019-9193',
                            'cve_severity': 'HIGH',
                            'cvss_version': 'v3.0',
                            'software_name': 'PostgreSQL',
                            'software_vendor': 'PostgreSQL Global Development Group'
                        },
                        {
                            'cvss_str': 'CVSS 8.1',
                            'cvss': 8.1,
                            'cve_id': 'CVE-2015-8960',
                            'cve_severity': 'HIGH',
                            'cvss_version': 'v3.0',
                            'software_name': 'Internet Explorer',
                            'software_vendor': 'Microsoft Corporation'
                        }
                    ]
                },
                'type': 'adapterdata',
                'entity': 'devices',
                'action_if_exists': 'update',
                'hidden_for_gui': True,
                'plugin_unique_name': 'static_analysis_0',
                'plugin_name': 'static_analysis',
                'accurate_for_datetime': '2020-10-20T10:05:40.545Z',
                'associated_adapter_plugin_name': 'kaseya_adapter'
            }
        ],
        'has_notes': False,
        'adapter_list_length': 1,
        'preferred_fields': {
            'hostname_preferred': 'EC2AMAZ-V8E9DHF',
            'os': {
                'type_preferred': 'Windows',
                'distribution_preferred': 'Server 2016',
                'os_str_preferred': 'windows 2016 server datacenter x64 edition  build 14393',
                'bitness_preferred': 64
            },
            'network_interfaces': {
                'mac_preferred': [
                    '06:DE:D4:0F:B4:18'
                ],
                'ips_preferred': [
                    '10.0.2.178'
                ]
            },
            'domain_preferred': 'TESTDOMAIN'
        }
    },
    {
        'internal_axon_id': 'c06d5fd09a324eb91293c9ec7dcc14b6',
        'accurate_for_datetime': '2020-10-20T10:07:21.545Z',
        'adapters': [
            {
                'client_used': 'PREVIEW6.KASEYA.NET',
                'plugin_type': 'Adapter',
                'plugin_name': 'kaseya_adapter',
                'plugin_unique_name': 'kaseya_adapter_0',
                'type': 'entitydata',
                'accurate_for_datetime': '2020-10-20T09:59:18.308Z',
                'data': {
                    'id': '41731352988141242425148718_WIN-D14VSGS3C0G',
                    'name': 'win-d14vsgs3c0g.base.myOrg',
                    'os': {
                        'type': 'Windows',
                        'distribution': 'Server 2012 R2',
                        'bitness': 64,
                        'os_str': 'windows 2012 r2 server standard x64 edition  build 9600',
                        'is_windows_server': True,
                        'type_distribution': 'Windows Server 2012 R2'
                    },
                    'hostname': 'WIN-D14VSGS3C0G',
                    'last_seen': '2020-10-13T10:14:50.770Z',
                    'time_zone': 'UTC',
                    'total_physical_memory': 8.0,
                    'device_manufacturer': 'Xen',
                    'network_interfaces': [
                        {
                            'mac': '06:B9:C8:89:0D:00',
                            'ips': [
                                '10.0.2.147'
                            ],
                            'ips_v4': [
                                '10.0.2.147'
                            ],
                            'ips_v4_raw': [
                                167772819
                            ],
                            'ips_raw': [
                                167772819
                            ]
                        }
                    ],
                    'agent_id': '538683541694784',
                    'installed_software': [
                        {
                            'version_raw': '000000006000000070000000500000177',
                            'name_version': 'Cloud Workload Protection-6.7.5.177',
                            'name': 'Cloud Workload Protection',
                            'version': '6.7.5.177',
                            'vendor': 'Symantec',
                            'description': 'Setup Launcher Unicode',
                            'path': 'C:\\Users\\Administrator\\Desktop\\agent.exe'
                        }],
                    'agent_versions': [
                        {
                            'adapter_name': 'Kaseya Agent',
                            'agent_version': '9050016'
                        }
                    ],
                    'domain': 'TESTDOMAIN',
                    'connected_devices': [],
                    'fetch_time': '2020-10-20T09:59:18.153Z',
                    'adapter_properties': [
                        'Agent',
                        'Manager'
                    ],
                    'accurate_for_datetime': '2020-10-20T09:59:18.308Z',
                    'first_fetch_time': '2020-10-20T09:59:18.153Z',
                    'pretty_id': 'AX-1'
                },
                'quick_id': 'kaseya_adapter_0!41731352988141242425148718_WIN-D14VSGS3C0G'
            }
        ],
        'tags': [
            {
                'association_type': 'Tag',
                'associated_adapters': [
                    [
                        'kaseya_adapter_0',
                        '41731352988141242425148718_WIN-D14VSGS3C0G'
                    ]
                ],
                'name': 'static_analysis_0',
                'data': {
                    'id': 'static_analysis_0!cve!c06d5fd09a324eb91293c9ec7dcc14b6',
                    'software_cves': [
                        {
                            'cvss_str': 'CVSS 7.2',
                            'cvss': 7.2,
                            'cve_id': 'CVE-2019-9193',
                            'cve_severity': 'HIGH',
                            'cvss_version': 'v3.0',
                            'software_name': 'PostgreSQL',
                            'software_vendor': 'PostgreSQL Global Development Group'
                        },
                        {
                            'cvss_str': 'CVSS 7.5',
                            'cvss': 7.5,
                            'cve_id': 'CVE-2007-5090',
                            'cve_severity': 'HIGH',
                            'cvss_version': 'v2.0',
                            'software_name': 'Microsoft SQL Server',
                            'software_vendor': 'Microsoft Corporation'
                        }
                    ]
                },
                'type': 'adapterdata',
                'entity': 'devices',
                'action_if_exists': 'update',
                'hidden_for_gui': True,
                'plugin_unique_name': 'static_analysis_0',
                'plugin_name': 'static_analysis',
                'accurate_for_datetime': '2020-10-20T10:07:21.545Z',
                'associated_adapter_plugin_name': 'kaseya_adapter'
            }
        ],
        'has_notes': False,
        'adapter_list_length': 1,
        'preferred_fields': {
            'hostname_preferred': 'WIN-D14VSGS3C0G',
            'os': {
                'type_preferred': 'Windows',
                'distribution_preferred': 'Server 2012 R2',
                'os_str_preferred': 'windows 2012 r2 server standard x64 edition  build 9600',
                'bitness_preferred': 64
            },
            'network_interfaces': {
                'mac_preferred': [
                    '06:B9:C8:89:0D:00'
                ],
                'ips_preferred': [
                    '10.0.2.147'
                ]
            },
            'domain_preferred': 'TESTDOMAIN'
        }
    }
]
