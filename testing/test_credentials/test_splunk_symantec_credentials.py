from test_credentials.test_splunk_credentials import *
splunk_details['online_hours'] = '24'

FETCHED_DEVICE_EXAMPLE = {
    'os': {
        "bitness": None,
        "distribution": "10",
                        "type": "Windows"
    },
    "hostname": "Axonius-Ofri",
    "id": "Axonius-Ofri",
    "network_interfaces": [
        {
            "ips": [
                "192.168.6.1"
            ],
            "mac": "00-50-56-c0-00-01"
        },
        {
            "ips": [
                "192.168.19.1"
            ],
            "mac": "00-50-56-c0-00-08"
        },
        {
            "ips": [
                "169.254.19.108"
            ],
            "mac": "f8-59-71-94-58-09"
        }
    ],
    "raw": {
        "_id": "2018-01-04 13:43:15+00:00",
        "host": {
            "category": "0",
            "engine": "Symantec Endpoint Protection -- Engine version: 14.0.3752",
            "level": "Info",
            "name": "Axonius-Ofri",
            "network": [
                {
                    "desc": "VMware Virtual Ethernet Adapter for VMnet",
                    "index": "0",
                    "ip": "192.168.6.1",
                    "mac": "00-50-56-c0-00-01",
                    "name": "VMware Network Adapter VMnet1"
                },
                {
                    "desc": "VMware Virtual Ethernet Adapter for VMnet",
                    "index": "1",
                    "ip": "192.168.19.1",
                    "mac": "00-50-56-c0-00-08",
                    "name": "VMware Network Adapter VMnet8"
                },
                {
                    "desc": "Intel(R) Dual Band Wireless-AC 826",
                    "index": "2",
                    "ip": "169.254.19.108",
                    "mac": "f8-59-71-94-58-09",
                    "name": "Wi-Fi"
                }
            ],
            "network_raw": " No.0  'VMware Network Adapter VMnet1'  00-50-56-c0-00-01  'VMware Virtual Ethernet Adapter for VMnet1' 192.168.6.1   No.1  'VMware Network Adapter VMnet8'  00-50-56-c0-00-08  'VMware Virtual Ethernet Adapter for VMnet8' 192.168.19.1   No.2  'Wi-Fi'  f8-59-71-94-58-09  'Intel(R) Dual Band Wireless-AC 8265' 169.254.19.108",
            "os": "Windows 10 (10.0.16299 ) ",
            "raw": "2017-12-18 09:47:06,Info,Axonius-Ofri,Category: 0,Smc,Symantec Endpoint Protection -- Engine version: 14.0.3752  Windows Version info:  Operating System: Windows 10 (10.0.16299 )  Network  info:  No.0  'VMware Network Adapter VMnet1'  00-50-56-c0-00-01  'VMware Virtual Ethernet Adapter for VMnet1' 192.168.6.1   No.1  'VMware Network Adapter VMnet8'  00-50-56-c0-00-08  'VMware Virtual Ethernet Adapter for VMnet8' 192.168.19.1   No.2  'Wi-Fi'  f8-59-71-94-58-09  'Intel(R) Dual Band Wireless-AC 8265' 169.254.19.108",
            "timestamp": "2017-12-18 09:47:06",
            "type": "symantec_win",
            "windows_version_info": ""
        },
        "name": "Axonius-Ofri"
    }
}
