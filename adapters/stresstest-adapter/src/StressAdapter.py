"""
StressAdapter.py: An adapter for stress testing
"""

from axonius.AdapterBase import AdapterBase


class StressAdapter(AdapterBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)

    def _query_devices_by_client(self, client_name, client_data):
        def _gen_data():
            return {
                "config": {
                    "annotation": "",
                    "cpuReservation": 0,
                    "guestFullName": "FreeBSD (64-bit)",
                    "guestId": "freebsd64Guest",
                    "installBootRequired": False,
                    "instanceUuid": "521690a4-7434-7dd4-ff4e-9ff4a4274246",
                    "memoryReservation": 0,
                    "memorySizeMB": 8192,
                    "name": "storageserver",
                    "numCpu": 2,
                    "numEthernetCards": 1,
                    "numVirtualDisks": 2,
                    "template": False,
                    "uuid": "564d3a19-50f6-9569-ce0c-af0ba5b594f8",
                    "vmPathName": "[sata-disk] storage-server/storage-server.vmx"
                },
                "customValue": {},
                "guest": {
                    "guestFullName": "FreeBSD (64-bit)",
                    "guestId": "freebsd64Guest",
                    "hostName": "storage.axonius.local",
                    "ipAddress": "192.168.20.3",
                    "toolsRunningStatus": "guestToolsRunning",
                    "toolsStatus": "toolsOk",
                    "toolsVersionStatus": "guestToolsUnmanaged"
                },
                "networking": [
                    {
                        "connected": True,
                        "deviceConfigId": 4000,
                        "ipAddresses": [
                            {
                                "ipAddress": "192.168.20.3",
                                "prefixLength": 24,
                                "state": "preferred"
                            }
                        ],
                        "macAddress": "00:0c:29:b5:94:f8",
                        "network": "VM Network"
                    }
                ],
                "overallStatus": {},
                "quickStats": {
                    "balloonedMemory": 0,
                    "compressedMemory": 0,
                    "consumedOverheadMemory": 46,
                    "distributedCpuEntitlement": 0,
                    "distributedMemoryEntitlement": 0,
                    "ftLatencyStatus": "gray",
                    "ftLogBandwidth": -1,
                    "ftSecondaryLatency": -1,
                    "guestHeartbeatStatus": "green",
                    "guestMemoryUsage": 573,
                    "hostMemoryUsage": 8208,
                    "overallCpuDemand": 104,
                    "overallCpuUsage": 104,
                    "privateMemory": 8162,
                    "sharedMemory": 0,
                    "staticCpuEntitlement": 0,
                    "staticMemoryEntitlement": 0,
                    "swappedMemory": 0,
                    "uptimeSeconds": 8018340
                },
                "runtime": {
                    "bootTime": "Fri, 01 Sep 2017 23:08:27 GMT",
                    "connectionState": "connected",
                    "consolidationNeeded": False,
                    "faultToleranceState": "notConfigured",
                    "maxCpuUsage": 4194,
                    "maxMemoryUsage": 8192,
                    "numMksConnections": 0,
                    "onlineStandby": False,
                    "powerState": "poweredOn",
                    "recordReplayState": "inactive",
                    "suspendInterval": 0,
                    "toolsInstallerMounted": False
                },
            }

        return [
            ({**_gen_data(), **{'name_blat': client_name, 'index': i}}) for i in range(client_data)
        ]

    def _clients_schema(self):
        return {
            "properties": {
                "device_count": {
                    "type": "number"
                },
                "name": {
                    "type": "string"
                }
            },
            "required": [
                "device_count",
                "name"
            ],
            "type": "object"
        }

    def _parse_raw_data(self, raw_data):
        for x in raw_data:
            yield {
                'id': f"{x['name_blat']}-{x['index']}",
                'raw': x,
                'name': f"avigdor no# {x['index']}"
            }

    def _get_client_id(self, client_config):
        return clients_config['name']

    def connect_client(self, client_config):
        return client_config['device_count']
