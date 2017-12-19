"""
StressAdapter.py: An adapter for stress testing.

We took most of the data from the ESX Adapter, but since it does not return so much things that can be currently
parsed (most of the fields will stay raw) we added manually fields that will be parsed values. So eventually
this is an imaginary adapter.
"""

import uuid
import time
import random
from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os

OPERATION_SYSTEMS_EXAMPLES = [
    "Windows XP", "Windows 7", "Windows 8", "Windows 10",
    "Ubuntu 12.04", "Ubuntu 14.04", "Ubuntu 16.04",
    "FreeBSD", "Fedora 21", "Fedora 22", "Fedora 23", "Fedora 24", "Fedora 25", "Fedora 26",
    "Mac OS X 10.7 Lion", "OS X 10.8 Mountain Lion", "OS X 10.9 Mavericks", "OS X 10.10 Yosemite",
    "OS X 10.11 El Capitan"
]


class StressAdapter(AdapterBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)
        self.initial_devices_db = {}

    def _generate_initial_devices_db(self, client_name, device_count):
        """
        Generates the initial devices db. We are going to return the same devices again and again (most of the data
        will not change) but some of it will. So we randomize the initial data that will not be changed.
        :param client_name: The name of the client to which the stressadapter is connected.
        :param device_count: the amount of devices to generate.
        :return: a list of such devices.
        """

        if device_count > 0xffff:
            # We don't support it mostly because of our network interfaces generation.
            raise NotImplemented("Stress adapter does not support more than 0xffff devices for the same client.")

        list_of_devices = []

        for i in range(device_count):
            device_os = "{0} ({1})".format(random.choice(OPERATION_SYSTEMS_EXAMPLES),
                                           random.choice(["32 bit", "64 bit"]))
            device_name = f"vm-{i}"
            device_uuid = str(uuid.uuid4())

            device_data = {}
            device_data.update({
                "config": {
                    "annotation": "",
                    "cpuReservation": 0,
                    "guestFullName": device_os,
                    "guestId": "localGuestID",
                    "installBootRequired": False,
                    "instanceUuid": device_uuid,
                    "memoryReservation": 0,
                    "memorySizeMB": random.choice([1024, 2048, 4096, 8192]),
                    "name": device_name,
                    "numCpu": random.choice([1, 2, 4, 8]),
                    "numEthernetCards": random.choice([1, 2]),
                    "numVirtualDisks": random.choice([1, 2, 3, 4]),
                    "template": False,
                    "uuid": device_uuid,
                    "vmPathName": f"[sata-disk] {device_name}/{device_name}-1.vmx"
                },
                "customValue": {},
                "overallStatus": {},
                "quickStats": {
                    "balloonedMemory": 0,
                    "compressedMemory": 0,
                    "consumedOverheadMemory": random.randint(20, 100),
                    "distributedCpuEntitlement": 0,
                    "distributedMemoryEntitlement": 0,
                    "ftLatencyStatus": "gray",
                    "ftLogBandwidth": -1,
                    "ftSecondaryLatency": -1,
                    "guestHeartbeatStatus": "green",
                    "guestMemoryUsage": random.randint(128, 1024),
                    "hostMemoryUsage": random.randint(4096, 8192),
                    "overallCpuDemand": random.randint(60, 100),
                    "overallCpuUsage": random.randint(60, 100),
                    "privateMemory": 8162,
                    "sharedMemory": 0,
                    "staticCpuEntitlement": 0,
                    "staticMemoryEntitlement": 0,
                    "swappedMemory": 0,
                    "uptimeSeconds": random.randint(10000, 20000)  # No correlation to ["runtime"]["bootTime"]
                },
                "sa_name": client_name,
                "index": i
            })

            device_data["runtime"] = {
                "bootTime": str(time.ctime(time.time() - 10 * i)),  # Each vm was created after 10 seconds distance
                "connectionState": "connected",
                "consolidationNeeded": False,
                "faultToleranceState": "notConfigured",
                "maxCpuUsage": random.randint(1000, 5000),
                "maxMemoryUsage": device_data["config"]["memorySizeMB"],
                "numMksConnections": 0,
                "onlineStandby": False,
                "powerState": "poweredOn",
                "recordReplayState": "inactive",
                "suspendInterval": 0,
                "toolsInstallerMounted": False
            }

            device_data["networking"] = []
            for j in range(device_data["config"]["numEthernetCards"]):
                device_data["networking"].append({
                    "connected": True,
                    "deviceConfigId": 4000,
                    "ipAddresses": [
                        {
                            "ipAddress": "{0}.{1}.{2}".format(["192.168", "10.0"][j], int(i / 256), i % 256),
                            "prefixLength": 16,
                            "state": "preferred"
                        }
                    ],
                    "macAddress": ":".join(["%0.2x" % random.randint(0, 0xff) for k in range(6)]),
                    "network": f"{client_name} Network"
                })

            device_data["guest"] = {
                "guestFullName": device_os,
                "guestId": device_data["config"]["guestId"],
                "hostName": "{0}.stress.axonius".format(device_data["config"]["name"]),
                "ipAddress": device_data["networking"][0]["ipAddresses"][0]["ipAddress"],   # The first ip.
                "toolsRunningStatus": "guestToolsRunning",
                "toolsStatus": "toolsOk",
                "toolsVersionStatus": "guestToolsUnmanaged"
            }

            list_of_devices.append(device_data)

        return list_of_devices

    def _query_devices_by_client(self, client_name, client_data):

        if client_name not in self.initial_devices_db:
            self.initial_devices_db[client_name] = self._generate_initial_devices_db(client_name, client_data)

        return self.initial_devices_db[client_name]

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
                'id': f"{x['sa_name']}-{x['index']}",
                'name': f"avigdor no# {x['index']}",
                'OS': figure_out_os(x['config']['guestFullName']),
                'network_interfaces': self._parse_network_device(x.get('networking', [])),
                'hostname': x['guest'].get('hostName'),
                'vmToolsStatus': x['guest'].get('toolsStatus'),
                'raw': x,
            }

    def _parse_network_device(self, raw_networks):
        """
        Parse a network device as received from vCenterAPI
        :param raw_network: raw networks from ESX
        :return: iter(dict)
        """
        for raw_network in raw_networks:
            ip_to_return = [addr['ipAddress'] for addr in raw_network.get('ipAddresses', [])]
            if len(ip_to_return) != 0:  # Return only if has an IP address
                yield {
                    "MAC": raw_network.get('macAddress'),
                    "IP": ip_to_return,
                    # in vCenter/ESX it's not trivial to figure out the 'public IP'
                    # the public IP is in the 'simple case' the public IP of the host machine (which we also
                    # don't know) but in other cases the host may be connected to multiple network devices
                    # itself, all of which aren't necessarily accessible by us, so we leave this blank :)
                }

    def _get_client_id(self, client_config):
        return client_config['name']

    def _connect_client(self, client_config):
        return client_config['device_count']
