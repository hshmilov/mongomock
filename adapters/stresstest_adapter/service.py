import uuid
import time
import random
from datetime import datetime

from axonius.adapter_base import AdapterBase
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file

OPERATION_SYSTEMS_EXAMPLES = [
    "Windows XP", "Windows 7", "Windows 8", "Windows 10",
    "Ubuntu 12.04", "Ubuntu 14.04", "Ubuntu 16.04",
    "FreeBSD", "Fedora 21", "Fedora 22", "Fedora 23", "Fedora 24", "Fedora 25", "Fedora 26",
    "Mac OS X 10.7 Lion", "OS X 10.8 Mountain Lion", "OS X 10.9 Mavericks", "OS X 10.10 Yosemite",
    "OS X 10.11 El Capitan"
]


class StresstestAdapter(AdapterBase):
    """
    An adapter for stress testing.

    We took most of the data from the ESX Adapter, but since it does not return so much things that can be currently
    parsed (most of the fields will stay raw) we added manually fields that will be parsed values. So eventually
    this is an imaginary adapter.
    """

    class MyDeviceAdapter(DeviceAdapter):
        vm_tools_status = Field(str, 'VM Tools Status')
        test_hyperlinks_str = Field(str, 'Test External Link String Hyperlink')
        test_hyperlinks_int = Field(int, 'Test External Link Int Hyperlink')
        test2_hyperlinks_str = Field(str, 'Test Query Link String Hyperlink')
        test2_hyperlinks_int = Field(int, 'Test Query Link Int Hyperlink')
        random_text_for_love_and_prosperity = Field(str, 'Lovely number')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)
        self.initial_devices_db = {}

    def _generate_initial_devices_db(self, client_name, device_count):
        """
        Generates the initial devices db. We are going to return the same devices again and again (most of the data
        will not change) but some of it will. So we randomize the initial data that will not be changed.
        :param client_name: The name of the client to which the stressadapter is connected.
        :param device_count: the amount of devices to generate.
        :return: a list of such devices.
        """

        if device_count > 0xffffff:
            # We don't support it mostly because of our network interfaces generation.
            raise NotImplementedError("Stress adapter does not support more than 0xffff devices for the same client.")

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
                            "ipAddress": "{0}.{1}.{2}.{3}".format("10",
                                                                  int((i / 256) / 256), int((i / 256) % 256), i % 256),
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
            "items": [
                {
                    "name": "device_count",
                    "title": "Device Count",
                    "type": "number"
                },
                {
                    "name": "name",
                    "title": "Server Name",
                    "type": "string"
                },
                {
                    "name": "default",
                    "title": "Testing default value",
                    "type": "number",
                    "default": 5
                }
            ],
            "required": [
                "device_count",
                "name"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._new_device_adapter()
            device.random_text_for_love_and_prosperity = str(random.randint(10, 100))
            device.id = f"{device_raw['sa_name']}-{device_raw['index']}"
            device.part_of_domain = True
            device.name = f"avigdor no# {device_raw['index']}"
            device.figure_os(device_raw['config']['guestFullName'])
            for iface in device_raw.get('networking', []):
                ips = [addr['ipAddress'] for addr in iface.get('ipAddresses', [])]
                if ips:
                    device.add_nic(iface.get('macAddress'), ips)
            device.hostname = device_raw['guest'].get('hostName')
            device.vm_tools_status = device_raw['guest'].get('toolsStatus')
            device.last_seen = datetime.now()

            # statistically proven to be the luckiest number, guaranteed to provide prosperity
            device.test_hyperlinks_str = 'seven'
            device.test_hyperlinks_int = 7

            # twice as lucky: It's the age of consent in the Glorious Nation of Kazakhstan
            device.test2_hyperlinks_str = 'fourteen'
            device.test2_hyperlinks_int = 14

            device.set_raw(device_raw)
            yield device

    def _test_reachability(self, client_config):
        return client_config['name']

    def _get_client_id(self, client_config):
        return client_config['name']

    def _connect_client(self, client_config):
        return client_config['device_count']

    @classmethod
    def adapter_properties(cls):
        return []
