# XXX: do not import from axonius libs here
import requests

AXONIUS_URL = "https://localhost"

AXONIUS_API = f"{AXONIUS_URL}/api/V1"

USERNAME = "admin"
PASSWORD = "Password"

TRIGGERS_DEFAULT_VALUES = {'every_discovery': False,
                           'new_entities': False,
                           'previous_entities': False,
                           'above': 0,
                           'below': 0,
                           }


def get_devices():
    params = {}

    # These paramters are REQUIRED. This will get first 50 devices.
    params["skip"] = 70
    params["limit"] = 50

    requests.get(f"{AXONIUS_API}/devices", params=params, auth=(USERNAME, PASSWORD))
    # The request would look like this
    # https://localhost/api/V1/devices?limit=50&skip=170

    # This would query a max of 50 devices with no filters on either the devices themselves or their fields
    # and will skip the first 170 devices.

    # An example response would look like this:
    """
    {
    "page": {
        "number": 1,
        "size": 2,
        "totalPages": 1,
        "totalResources": 2
    },
    "assets": [
        {
            "adapter_list_length": 1,
            "adapters": [
                "eset_adapter"
            ],
            "adapters_data": [
                {
                    "eset_adapter": {
                        "accurate_for_datetime": "Sun, 29 Jul 2018 15:44:39 GMT",
                        "hostname": "windows8.testdomain.test",
                        "id": "00:0C:29:80:0E:60windows8.testdomain.test",
                        "last_seen": "Sun, 29 Jul 2018 15:43:53 GMT",
                        "network_interfaces": [
                            {
                                "ips": [
                                    "192.168.20.9"
                                ],
                                "ips_raw": [
                                    3232240649
                                ],
                                "mac": "00:0C:29:80:0E:60",
                                "manufacturer": "VMware, Inc. (3401 Hillview Avenue Palo Alto CA US 94304 )"
                            }
                        ],
                        "os": {
                            "bitness": 64,
                            "distribution": "8",
                            "type": "Windows"
                        },
                        "pretty_id": "AX-61",
                        "raw": {
                            "Adapter IPv4 address": "192.168.20.9",
                            "Adapter IPv6 address": "",
                            "Computer name": "windows8.testdomain.test",
                            "Last connected": "2018-07-29 15:43:53",
                            "MAC address": "00-0C-29-80-0E-60",
                            "OS name": "Microsoft Windows 8.1 Enterprise",
                            "OS platform": "64-bit",
                            "OS type": "Microsoft Windows",
                            "OS version": "6.3.9600"
                        }
                    }
                }
            ],
            "date_fetched": "2018-07-29 14:39:59+00:00",
            "generic_data": [
                {
                    "accurate_for_datetime": "Sun, 29 Jul 2018 14:40:56 GMT",
                    "action_if_exists": "replace",
                    "associated_adapters": [
                        [
                            "active_directory_adapter_24640",
                            "CN=WINDOWS8,CN=Computers,DC=TestDomain,DC=test"
                        ]
                    ],
                    "association_type": "Tag",
                    "data": false,
                    "entity": "devices",
                    "name": "IP Conflicts",
                    "plugin_name": "active_directory_adapter",
                    "plugin_unique_name": "active_directory_adapter_24640",
                    "type": "data"
                }
            ],
            "internal_axon_id": "f4962e92eaa44b28b14863efdeaac5f3",
            "labels": [],
            "specific_data": [
                {
                    "accurate_for_datetime": "Sun, 29 Jul 2018 15:44:39 GMT",
                    "adapter_properties": [
                        "Endpoint_Protection_Platform",
                        "Agent",
                        "Manager"
                    ],
                    "client_used": "192.168.20.18:2223",
                    "data": {
                        "accurate_for_datetime": "Sun, 29 Jul 2018 15:44:39 GMT",
                        "hostname": "windows8.testdomain.test",
                        "id": "00:0C:29:80:0E:60windows8.testdomain.test",
                        "last_seen": "Sun, 29 Jul 2018 15:43:53 GMT",
                        "network_interfaces": [
                            {
                                "ips": [
                                    "192.168.20.9"
                                ],
                                "ips_raw": [
                                    3232240649
                                ],
                                "mac": "00:0C:29:80:0E:60",
                                "manufacturer": "VMware, Inc. (3401 Hillview Avenue Palo Alto CA US 94304 )"
                            }
                        ],
                        "os": {
                            "bitness": 64,
                            "distribution": "8",
                            "type": "Windows"
                        },
                        "pretty_id": "AX-61",
                        "raw": {
                            "Adapter IPv4 address": "192.168.20.9",
                            "Adapter IPv6 address": "",
                            "Computer name": "windows8.testdomain.test",
                            "Last connected": "2018-07-29 15:43:53",
                            "MAC address": "00-0C-29-80-0E-60",
                            "OS name": "Microsoft Windows 8.1 Enterprise",
                            "OS platform": "64-bit",
                            "OS type": "Microsoft Windows",
                            "OS version": "6.3.9600"
                        }
                    },
                    "plugin_name": "eset_adapter",
                    "plugin_type": "Adapter",
                    "plugin_unique_name": "eset_adapter_39094",
                    "type": "entitydata"
                }
            ],
            "unique_adapter_names": [
                "eset_adapter_39094"
            ],
            "uuid": "5b5dd1bff1e64e0014f18b39"
        },
        {
            "adapter_list_length": 1,
            "adapters": [
                "eset_adapter"
            ],
            "adapters_data": [
                {
                    "eset_adapter": {
                        "accurate_for_datetime": "Sun, 29 Jul 2018 15:44:39 GMT",
                        "hostname": "eset.axonius.lan",
                        "id": "00:50:56:91:A6:6Beset.axonius.lan",
                        "last_seen": "Sun, 29 Jul 2018 15:43:52 GMT",
                        "network_interfaces": [
                            {
                                "ips": [
                                    "192.168.20.18"
                                ],
                                "ips_raw": [
                                    3232240658
                                ],
                                "mac": "00:50:56:91:A6:6B",
                                "manufacturer": "VMware, Inc. (3401 Hillview Avenue PALO ALTO CA US 94304 )"
                            }
                        ],
                        "os": {
                            "bitness": 64,
                            "type": "Linux"
                        },
                        "pretty_id": "AX-62",
                        "raw": {
                            "Adapter IPv4 address": "192.168.20.18",
                            "Adapter IPv6 address": "",
                            "Computer name": "eset.axonius.lan",
                            "Last connected": "2018-07-29 15:43:52",
                            "MAC address": "00-50-56-91-A6-6B",
                            "OS name": "CentOS",
                            "OS platform": "64-bit",
                            "OS type": "Linux",
                            "OS version": "7.3.1611"
                        }
                    }
                }
            ],
            "date_fetched": "2018-07-29 14:39:59+00:00",
            "generic_data": [],
            "internal_axon_id": "e0a1cfff60da4b9ba4313d42ed29b1fc",
            "labels": [],
            "specific_data": [
                {
                    "accurate_for_datetime": "Sun, 29 Jul 2018 15:44:39 GMT",
                    "adapter_properties": [
                        "Endpoint_Protection_Platform",
                        "Agent",
                        "Manager"
                    ],
                    "client_used": "192.168.20.18:2223",
                    "data": {
                        "accurate_for_datetime": "Sun, 29 Jul 2018 15:44:39 GMT",
                        "hostname": "eset.axonius.lan",
                        "id": "00:50:56:91:A6:6Beset.axonius.lan",
                        "last_seen": "Sun, 29 Jul 2018 15:43:52 GMT",
                        "network_interfaces": [
                            {
                                "ips": [
                                    "192.168.20.18"
                                ],
                                "ips_raw": [
                                    3232240658
                                ],
                                "mac": "00:50:56:91:A6:6B",
                                "manufacturer": "VMware, Inc. (3401 Hillview Avenue PALO ALTO CA US 94304 )"
                            }
                        ],
                        "os": {
                            "bitness": 64,
                            "type": "Linux"
                        },
                        "pretty_id": "AX-62",
                        "raw": {
                            "Adapter IPv4 address": "192.168.20.18",
                            "Adapter IPv6 address": "",
                            "Computer name": "eset.axonius.lan",
                            "Last connected": "2018-07-29 15:43:52",
                            "MAC address": "00-50-56-91-A6-6B",
                            "OS name": "CentOS",
                            "OS platform": "64-bit",
                            "OS type": "Linux",
                            "OS version": "7.3.1611"
                        }
                    },
                    "plugin_name": "eset_adapter",
                    "plugin_type": "Adapter",
                    "plugin_unique_name": "eset_adapter_39094",
                    "type": "entitydata"
                }
            ],
            "unique_adapter_names": [
                "eset_adapter_39094"
            ],
            "uuid": "5b5dd1bff1e64e0014f18b35"
        }
    ]
}
    """

    params = {}

    # These paramters are REQUIRED. This will get first 50 devices.
    params["skip"] = 0
    params["limit"] = 50

    # This will tell the api to bring these specific fields.
    params["fields"] = ",".join(
        ["adapters", "specific_data.data.hostname", "specific_data.data.name", "specific_data.data.os.type",
         "specific_data.data.network_interfaces.ips", "specific_data.data.network_interfaces.mac", "labels"])

    # This a url encoded filter that brings all the devices that were correlated from Rapid 7 Nexpose and Active Directory adapters.
    # adapters%20==%20%22active_directory_adapter%22%20and%20adapters%20==%20%22nexpose_adapter%22
    params["filter"] = 'adapters == "active_directory_adapter" and adapters == "nexpose_adapter"'

    requests.get(f"{AXONIUS_API}/devices", params=params, auth=(USERNAME, PASSWORD))
    # The request would look like this
    # https://localhost/api/V1/devices?skip=0&limit=50&fields=adapters,specific_data.data.hostname,specific_data.data.name,specific_data.data.os.type,specific_data.data.network_interfaces.ips,specific_data.data.network_interfaces.mac,labels&filter=adapters%20==%20%22active_directory_adapter%22%20and%20adapters%20==%20%22nexpose_adapter%22

    # An example response would look like this:
    """
    {
    "page": {
        "number": 1,
        "size": 2,
        "totalPages": 1,
        "totalResources": 2
    },
    "assets": [
  {
    "adapter_list_length": 2, 
    "adapters": [
      "nexpose_adapter", 
      "active_directory_adapter"
    ], 
    "internal_axon_id": "8b45e72e83a1451785630501bdcda95b", 
    "labels": [
      "IP Conflicts"
    ], 
    "specific_data.data.hostname": [
      "DESKTOP-MPP10U1"
    ], 
    "specific_data.data.name": [], 
    "specific_data.data.network_interfaces.ips": [
      "192.168.20.19"
    ], 
    "specific_data.data.network_interfaces.mac": [
      "00:0C:29:45:B8:19"
    ], 
    "specific_data.data.os.type": [
      "Windows"
    ], 
    "unique_adapter_names": [
      "nexpose_adapter_12580", 
      "active_directory_adapter_12103"
    ]
  }, 
  {
    "adapter_list_length": 2, 
    "adapters": [
      "nexpose_adapter", 
      "active_directory_adapter"
    ], 
    "internal_axon_id": "643438a7e26e4942ab74b406a43a58c5", 
    "labels": [], 
    "specific_data.data.hostname": [
      "DC4"
    ], 
    "specific_data.data.name": [], 
    "specific_data.data.network_interfaces.ips": [
      "192.168.20.17"
    ], 
    "specific_data.data.network_interfaces.mac": [
      "00:0C:29:B6:DA:46"
    ], 
    "specific_data.data.os.type": [
      "Windows"
    ], 
    "unique_adapter_names": [
      "nexpose_adapter_12580", 
      "active_directory_adapter_12103"
    ]
  }
]
    """


def get_device_by_id():
    device_id = "8b45e72e83a1451785630501bdcda95b"
    requests.get(f"{AXONIUS_API}/devices/{device_id}", auth=(USERNAME, PASSWORD))

    # Will return a specific device:
    """
    {
    "adapter_list_length": 2, 
    "adapters": [
      "nexpose_adapter", 
      "active_directory_adapter"
    ], 
    "internal_axon_id": "8b45e72e83a1451785630501bdcda95b", 
    "labels": [
      "IP Conflicts"
    ], 
    "specific_data.data.hostname": [
      "DESKTOP-MPP10U1"
    ], 
    "specific_data.data.name": [], 
    "specific_data.data.network_interfaces.ips": [
      "192.168.20.19"
    ], 
    "specific_data.data.network_interfaces.mac": [
      "00:0C:29:45:B8:19"
    ], 
    "specific_data.data.os.type": [
      "Windows"
    ], 
    "unique_adapter_names": [
      "nexpose_adapter_12580", 
      "active_directory_adapter_12103"
    ]
  }
    """


def get_device_views():
    params = {}

    # Bring the first 1000 device views
    params["limit"] = 1000
    params["skip"] = 0

    params['filter'] = "query_type=='saved'"

    # https://localhost/api/devices/views?limit=1000&skip=0&filter=query_type==%27saved%27
    requests.get(f"{AXONIUS_API}/devices/views", params=params, auth=(USERNAME, PASSWORD))

    """
    [
  {
    "date_fetched": "2018-07-06 17:41:22+00:00", 
    "name": "DEMO - nexpose adapter", 
    "query_type": "saved", 
    "timestamp": "Fri, 06 Jul 2018 17:41:22 GMT", 
    "uuid": "5b3fa9c2606ffc7a20e17767", 
    "view": {
      "coloumnSizes": [], 
      "fields": [
        "adapters", 
        "specific_data.data.hostname", 
        "specific_data.data.name", 
        "specific_data.data.os.type", 
        "specific_data.data.network_interfaces.ips", 
        "specific_data.data.network_interfaces.mac", 
        "labels"
      ], 
      "page": 0, 
      "pageSize": 20, 
      "query": {
        "filter": "adapters == 'nexpose_adapter'"
      }, 
      "sort": {
        "desc": true, 
        "field": ""
      }
    }
  }, 
  {
    "date_fetched": "2018-07-06 17:30:48+00:00", 
    "name": "Connected Hardware Information", 
    "query_type": "saved", 
    "timestamp": "Fri, 06 Jul 2018 17:30:48 GMT", 
    "uuid": "5b3fa748cb4e67002fc5959a", 
    "view": {
      "coloumnSizes": [], 
      "fields": [
        "adapters", 
        "specific_data.data.name", 
        "specific_data.data.connected_hardware.name", 
        "specific_data.data.connected_hardware.hw_id", 
        "specific_data.data.connected_hardware.manufacturer", 
        "specific_data.data.network_interfaces.ips", 
        "specific_data.data.network_interfaces.mac", 
        "specific_data.data.os.type", 
        "specific_data.data.hostname", 
        "labels"
      ], 
      "page": 0, 
      "pageSize": 20, 
      "query": {
        "expressions": [
          {
            "compOp": "exists", 
            "field": "specific_data.data.connected_hardware.name", 
            "i": 0, 
            "leftBracket": false, 
            "logicOp": "", 
            "not": false, 
            "rightBracket": false, 
            "value": null
          }
        ], 
        "filter": "(specific_data.data.connected_hardware.name == exists(true) and specific_data.data.connected_hardware.name != \"\")"
      }, 
      "sort": {
        "desc": true, 
        "field": ""
      }
    }
  }, 
  {
    "date_fetched": "2018-07-06 17:30:48+00:00", 
    "name": "Vulnerable Software Information", 
    "query_type": "saved", 
    "timestamp": "Fri, 06 Jul 2018 17:30:48 GMT", 
    "uuid": "5b3fa748cb4e67002fc59599", 
    "view": {
      "coloumnSizes": [], 
      "fields": [
        "adapters", 
        "specific_data.data.name", 
        "specific_data.data.software_cves.software_name", 
        "specific_data.data.software_cves.software_vendor", 
        "specific_data.data.software_cves.software_version", 
        "specific_data.data.software_cves.cve_id", 
        "specific_data.data.software_cves.cve_severity", 
        "specific_data.data.software_cves.cve_references", 
        "specific_data.data.software_cves.cve_description", 
        "specific_data.data.os.type", 
        "labels"
      ], 
      "page": 0, 
      "pageSize": 20, 
      "query": {
        "expressions": [
          {
            "compOp": "exists", 
            "field": "specific_data.data.software_cves.software_vendor", 
            "i": 0, 
            "leftBracket": false, 
            "logicOp": "", 
            "not": false, 
            "rightBracket": false, 
            "value": null
          }
        ], 
        "filter": "(specific_data.data.software_cves.software_vendor == exists(true) and specific_data.data.software_cves.software_vendor != \"\")"
      }, 
      "sort": {
        "desc": true, 
        "field": ""
      }
    }
  }]
    """


def create_new_device_view():
    data = {"name": "All Nexpose Scanned AD Devices", "view": {"page": 0, "pageSize": 20,
                                                               "fields": ["adapters", "specific_data.data.hostname",
                                                                          "specific_data.data.name",
                                                                          "specific_data.data.os.type",
                                                                          "specific_data.data.network_interfaces.ips",
                                                                          "specific_data.data.network_interfaces.mac",
                                                                          "labels"], "coloumnSizes": [], "query": {
                                                                   "filter": "adapters == \"active_directory_adapter\" and adapters == \"nexpose_adapter\"", "expressions": [
                                                                       {"logicOp": "", "not": False, "leftBracket": False, "field": "adapters", "compOp": "equals",
                                                                        "value": "active_directory_adapter", "rightBracket": False, "i": 0},
                                                                       {"logicOp": "and", "not": False, "leftBracket": False, "field": "adapters", "compOp": "equals",
                                                                        "value": "nexpose_adapter", "rightBracket": False, "i": 1}]}, "sort": {"field": "", "desc": True}},
            "query_type": "saved"}

    # Creates a new saved query named: "All Nexpose Scanned AD Devices" That gets all the devices that have been
    # queried from both Rapid 7 Nexpose and Active Directory
    requests.post(f"{AXONIUS_API}/devices/views", data=data, auth=(USERNAME, PASSWORD))


def delete_device_view():
    # Deletes all listed device views (by ID).
    data = ["5b3fbc3b606ffc7a20e1d837"]
    requests.delete(f"{AXONIUS_API}/devices/views", data=data, auth=(USERNAME, PASSWORD))


def get_users():
    params = {}

    # These parameters are REQUIRED. This will get first 50 users.
    params["skip"] = 0
    params["limit"] = 20

    # This will tell the api to bring these specific fields.
    params["fields"] = ",".join(
        ["specific_data.data.image", "specific_data.data.username", "specific_data.data.domain",
         "specific_data.data.last_seen", "specific_data.data.is_admin"])

    # This a url encoded filter that brings all the not local users.
    # specific_data.data.is_local%20==%20false
    params["filter"] = 'specific_data.data.is_local == false'
    requests.get(f"{AXONIUS_API}/users", params=params, auth=(USERNAME, PASSWORD))
    # https://localhost/api/V1/users?skip=0&limit=20&fields=specific_data.data.image,specific_data.data.username,specific_data.data.domain,specific_data.data.last_seen,specific_data.data.is_admin&filter=specific_data.data.is_local%20==%20false

    # An example response would look like this:
    """
    [
  {
    "adapter_list_length": 1, 
    "adapters": [
      "active_directory_adapter"
    ], 
    "internal_axon_id": "364d32967f7e448293e8cb886fb02e86", 
    "labels": [], 
    "specific_data.data.domain": "TestDomain.test", 
    "specific_data.data.image": null, 
    "specific_data.data.is_admin": null, 
    "specific_data.data.last_seen": "Thu, 05 Jul 2018 14:12:31 GMT", 
    "specific_data.data.username": "test_ldap_login_user", 
    "unique_adapter_names": [
      "active_directory_adapter_15855"
    ]
  }, 
  {
    "adapter_list_length": 1, 
    "adapters": [
      "active_directory_adapter"
    ], 
    "internal_axon_id": "daa251b408f7408a993765d92779db41", 
    "labels": [], 
    "specific_data.data.domain": "TestDomain.test", 
    "specific_data.data.image": null, 
    "specific_data.data.is_admin": null, 
    "specific_data.data.last_seen": null, 
    "specific_data.data.username": "RAINDOMAIN$", 
    "unique_adapter_names": [
      "active_directory_adapter_15855"
    ]
  }, 
  {
    "adapter_list_length": 1, 
    "adapters": [
      "active_directory_adapter"
    ], 
    "internal_axon_id": "55dd84002bf442a5b72d7b4667ead88b", 
    "labels": [], 
    "specific_data.data.domain": "TestDomain.test", 
    "specific_data.data.image": null, 
    "specific_data.data.is_admin": true, 
    "specific_data.data.last_seen": "Fri, 06 Jul 2018 13:56:29 GMT", 
    "specific_data.data.username": "Administrator", 
    "unique_adapter_names": [
      "active_directory_adapter_15855"
    ]
  }, 
  {
    "adapter_list_length": 1, 
    "adapters": [
      "active_directory_adapter"
    ], 
    "internal_axon_id": "45a5a75b934d4ae193c76edfff523eda", 
    "labels": [], 
    "specific_data.data.domain": "TestDomain.test", 
    "specific_data.data.image": null, 
    "specific_data.data.is_admin": null, 
    "specific_data.data.last_seen": null, 
    "specific_data.data.username": "WEST$", 
    "unique_adapter_names": [
      "active_directory_adapter_15855"
    ]
  }
]

    """


def get_user_by_id():
    user_id = "45a5a75b934d4ae193c76edfff523eda"
    requests.get(f"{AXONIUS_API}/devices/{user_id}", auth=(USERNAME, PASSWORD))

    # Will return a specific device:
    """
    {
    "adapter_list_length": 1, 
    "adapters": [
      "active_directory_adapter"
    ], 
    "internal_axon_id": "45a5a75b934d4ae193c76edfff523eda", 
    "labels": [], 
    "specific_data.data.domain": "TestDomain.test", 
    "specific_data.data.image": null, 
    "specific_data.data.is_admin": null, 
    "specific_data.data.last_seen": null, 
    "specific_data.data.username": "WEST$", 
    "unique_adapter_names": [
      "active_directory_adapter_15855"
    ]
  }"""


def get_users_view():
    params = {}

    # Brings the first 10000 saved user queries
    params["limit"] = 1000
    params["skip"] = 0

    params["filter"] = "query_type=='saved'"

    requests.get(f"{AXONIUS_API}/users/views", params=params, auth=(USERNAME, PASSWORD))
    # https://localhost/api/users/views?limit=1000&skip=0&filter=query_type==%27saved%27

    # Response would look like:
    """
    [
  {
    "date_fetched": "2018-07-06 17:30:49+00:00", 
    "name": "Not Local Users", 
    "query_type": "saved", 
    "timestamp": "Fri, 06 Jul 2018 17:42:18 GMT", 
    "uuid": "5b3fa749cb4e67002fc595b4", 
    "view": {
      "coloumnSizes": [], 
      "fields": [
        "specific_data.data.image", 
        "specific_data.data.username", 
        "specific_data.data.domain", 
        "specific_data.data.last_seen", 
        "specific_data.data.is_admin", 
        "specific_data.data.last_seen_in_devices"
      ], 
      "page": 0, 
      "pageSize": 20, 
      "query": {
        "expressions": [
          {
            "compOp": "true", 
            "field": "specific_data.data.is_local", 
            "i": 0, 
            "leftBracket": false, 
            "logicOp": "", 
            "not": false, 
            "rightBracket": false, 
            "value": ""
          }
        ], 
        "filter": "specific_data.data.is_local == true"
      }, 
      "sort": {
        "desc": true, 
        "field": ""
      }
    }
  }, 
  {
    "date_fetched": "2018-07-06 17:30:49+00:00", 
    "name": "Users Created in Last 30 Days", 
    "query_type": "saved", 
    "timestamp": "Fri, 06 Jul 2018 17:30:49 GMT", 
    "uuid": "5b3fa749cb4e67002fc595bc", 
    "view": {
      "coloumnSizes": [], 
      "fields": [
        "specific_data.data.username", 
        "specific_data.data.user_created", 
        "adapters", 
        "specific_data.data.domain"
      ], 
      "page": 0, 
      "pageSize": 20, 
      "query": {
        "expressions": [
          {
            "compOp": "days", 
            "field": "specific_data.data.user_created", 
            "i": 0, 
            "leftBracket": false, 
            "logicOp": "", 
            "not": false, 
            "rightBracket": false, 
            "value": 30
          }
        ], 
        "filter": "specific_data.data.user_created >= date(\"NOW - 30d\")"
      }, 
      "sort": {
        "desc": true, 
        "field": ""
      }
    }
  }, 
  {
    "date_fetched": "2018-07-06 17:30:49+00:00", 
    "name": "Users Created in Last 7 Days", 
    "query_type": "saved", 
    "timestamp": "Fri, 06 Jul 2018 17:30:49 GMT", 
    "uuid": "5b3fa749cb4e67002fc595bb", 
    "view": {
      "coloumnSizes": [], 
      "fields": [
        "specific_data.data.username", 
        "specific_data.data.user_created", 
        "adapters", 
        "specific_data.data.domain"
      ], 
      "page": 0, 
      "pageSize": 20, 
      "query": {
        "expressions": [
          {
            "compOp": "days", 
            "field": "specific_data.data.user_created", 
            "i": 0, 
            "leftBracket": false, 
            "logicOp": "", 
            "not": false, 
            "rightBracket": false, 
            "value": 7
          }
        ], 
        "filter": "specific_data.data.user_created >= date(\"NOW - 7d\")"
      }, 
      "sort": {
        "desc": true, 
        "field": ""
      }
    }
  }]
    """


def save_users_view():
    data = {"name": "Not Local Users", "view": {"page": 0, "pageSize": 20,
                                                "fields": ["specific_data.data.image", "specific_data.data.username",
                                                           "specific_data.data.domain", "specific_data.data.last_seen",
                                                           "specific_data.data.is_admin",
                                                           "specific_data.data.last_seen_in_devices"],
                                                "coloumnSizes": [],
                                                "query": {"filter": "specific_data.data.is_local == True",
                                                          "expressions": [
                                                              {"compOp": "True", "field": "specific_data.data.is_local",
                                                               "i": 0, "leftBracket": False, "logicOp": "",
                                                               "not": False, "rightBracket": False, "value": ""}]},
                                                "sort": {"desc": True, "field": ""}}, "query_type": "saved"}

    requests.post(f"{AXONIUS_API}/users/views", data=data, auth=(USERNAME, PASSWORD))


def delete_user_view():
    # Deletes all listed device views (by ID).
    data = ["5b3fa749cb4e67002fc595bb"]
    requests.delete(f"{AXONIUS_API}/users/views", data=data, auth=(USERNAME, PASSWORD))


def get_alerts():
    params = {}

    params["skip"] = None
    params["limit"] = None

    params["fields"] = ','.join(["name", "report_creation_time", "triggered", "view", "severity"])

    # This will get all the configured alerts
    requests.get(f"{AXONIUS_API}/alert", params=params, auth=(USERNAME, PASSWORD))
    # https://localhost/api/alert?skip=NaN&limit=0&fields=name,report_creation_time,triggered,view,severity

    # Response would look like:
    """
    [
  {
    "date_fetched": "2018-07-06 17:39:45+00:00", 
    "name": "Test Alert", 
    "report_creation_time": "Fri, 06 Jul 2018 17:39:45 GMT", 
    "severity": "warning", 
    "triggered": 0, 
    "uuid": "5b3fa9612af45000146561a9", 
    "view": "Not Local Users"
  }
]
    """


def delete_alert():
    alert_id = "5b3fa9612af45000146561a9"
    requests.delete(f"{AXONIUS_API}/alerts/{alert_id}", auth=(USERNAME, PASSWORD))

    # Response would be status code 200 (OK)


def put_alert():
    # Notice that id = "new" tells the api this is a new alert.
    # Triggers should contain all the triggers with true (or int above 0) on activated triggers.
    # Actions type should be one of thses:
    # tag_entities
    # create_service_now_computer
    # create_service_now_incident
    # notify_syslog
    # send_emails
    # create_notification
    # tag_entities
    trigger_dict = TRIGGERS_DEFAULT_VALUES
    trigger_dict['above'] = 1

    data = {"id": "new", "name": "Test Alert",
            "triggers": trigger_dict,
            "actions": [{"type": "create_notification"}], "view": "Not Local Users", "viewEntity": "users",
            "retrigger": True, "triggered": False, "severity": "warning"}

    requests.put(f"{AXONIUS_API}/alerts", data=data, auth=(USERNAME, PASSWORD))

    # Response is status code: 201 (Created).


def get_actions_to_run():
    requests.get(f"{AXONIUS_API}/actions", auth=(USERNAME, PASSWORD))

    # Response is status code: 200 and a list of actions that can be executed.
    # [
    #     "deploy",
    #     "shell"
    # ]


def run_actions():
    # data = { ...this.deploy.data, internal_axon_ids: this.devices}
    data = {
        "internal_axon_ids": ['8b45e72e83a1451785630501bdcda95b'],  # The device
        "action_name": 'Put File',
        "command": "echo 'Touched by axonius' > /home/ubuntu/axonius_file"
    }

    requests.post(f"{AXONIUS_API}/actions/shell", data=data, auth=(USERNAME, PASSWORD))

    # Response is status code: 200. The command will run on the requested device.

    with open('./script_file_to_run', 'r') as file_to_run:
        data = {
            "internal_axon_ids": ['8b45e72e83a1451785630501bdcda95b'],  # The device
            "action_name": 'Run Script File',
            "binary": file_to_run.read()
        }

        requests.post(f"{AXONIUS_API}/actions/deploy", data=data, auth=(USERNAME, PASSWORD))

    # Response is status code: 200. The script file was deployed and ran on the devices.


def get_all_labels():
    # This will return a list of strings that are all the labels in the system
    requests.get(f"{AXONIUS_API}/devices/labels", auth=(USERNAME, PASSWORD))
    requests.get(f"{AXONIUS_API}/users/labels", auth=(USERNAME, PASSWORD))


def add_labels():
    data = {
        'entities': ['internal_axon_id1', 'internal_axon_id2'],  # list of internal axon ids
        'labels': ['labels to add', 'another label']  # list of labels to add
    }
    requests.post(f"{AXONIUS_API}/devices/labels", auth=(USERNAME, PASSWORD), data=data)


def delete_labels():
    data = {
        'entities': ['internal_axon_id1', 'internal_axon_id2'],  # list of internal axon ids
        'labels': ['labels to add', 'another label']  # list of labels to remove
    }
    requests.delete(f"{AXONIUS_API}/devices/labels", auth=(USERNAME, PASSWORD), data=data)
