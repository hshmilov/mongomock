import json
import ipaddress

from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device import Device
from axonius.fields import ListField, Field
from axonius.parsing_utils import format_mac, parse_date, is_valid_ip
from axonius.utils.files import get_local_config_file
from epo_adapter.mcafee import client


EPO_HOST = 'host'
EPO_PORT = 'port'
PASS = 'password'
USER = 'user'

LEAF_NODE_TABLE = 'EPOLeafNode'


def get_all_linked_tables(table):
    """
    :param table: table data
    :return: list of tables linked by a foreign key
    """
    by_lines = table['foreignKeys'].strip().split("\n")[2:]
    foreign_tables = [line.split()[2] for line in by_lines]
    all_linked_tables = ",".join(foreign_tables)
    return all_linked_tables


def parse_network(device_raw, device, logger):
    mac = ''
    ip_list = set()

    raw_ipv4 = device_raw.get('EPOComputerProperties.IPV4x')
    parsed_ipv4 = None
    try:
        # epo is a motherfucker? Seems like he flips the msb of the binary repr of ip addr...
        ipv4 = (raw_ipv4 & 0xffffffff) ^ 0x80000000
        parsed_ipv4 = str(ipaddress.IPv4Address(ipv4))
        ip_list.add(parsed_ipv4)
    except:
        logger.info(f"Error reading IPv4 {raw_ipv4}")

    raw_ipv6 = device_raw.get('EPOComputerProperties.IPV6')
    if is_valid_ip(raw_ipv6) and raw_ipv6 is not None:
        ip_list.add(raw_ipv6.lower())

    try:
        ipv4mapped = ipaddress.IPv6Address(raw_ipv6).ipv4_mapped if is_valid_ip(raw_ipv6) else None
        if ipv4mapped and str(ipv4mapped) != parsed_ipv4:
            logger.info(
                f"ipv4/6 mismatch: raw4={raw_ipv4} raw6={raw_ipv6} parsed4={parsed_ipv4} ip4-6mapped={ipv4mapped}")
            if ipv4mapped:
                # epo's ipv4 reporting is problematic.
                # But we noticed that mapped ipv6 addresses tend to have the correct value
                # In such a case we add the mapped ipv4 address
                ip_list.add(str(ipv4mapped))
    except:
        logger.warning(f"Failed to populate populate ipv4/6 address raw_ipv4={raw_ipv4} raw_ipv6={raw_ipv6}")

    raw_mac = device_raw.get('EPOComputerProperties.NetAddress')
    try:
        mac = format_mac(raw_mac)
    except:
        logger.info(f"Failed formatting {raw_mac}")

    device.add_nic(mac, list(ip_list), logger)


class EpoAdapter(AdapterBase):
    """
    Connects axonius to mcafee epo
    """

    class MyDevice(Device):
        epo_products = ListField(str, "EPO Products")
        epo_agent_version = Field(str, "EPO Agent Version")

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": EPO_HOST,
                    "title": "Host",
                    "type": "string"
                },
                {
                    "name": EPO_PORT,
                    "title": "Port",
                    "type": "number"
                },
                {
                    "name": USER,
                    "title": "User",
                    "type": "string"
                },
                {
                    "name": PASS,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                EPO_PORT,
                EPO_HOST,
                PASS,
                USER
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in json.loads(devices_raw_data):
            epo_id = device_raw.get('EPOLeafNode.AgentGUID')
            if epo_id is None:
                # skipping devices without Agent-ID
                continue

            hostname = device_raw.get('EPOComputerProperties.IPHostName')
            if hostname is None or hostname == '':
                hostname = device_raw.get('EPOComputerProperties.ComputerName')

            if 'EPOLeafNode.LastUpdate' not in device_raw:
                # No date for this device, we don't want to enter devices with no date so continuing.
                self.logger.warning(f"Found device with no date. Not inserting to db. device name: {hostname}")
                continue

            device = self._new_device()
            device.hostname = hostname
            device.figure_os(device_raw.get('EPOLeafNode.os', ''))
            device.os.bitness = 64 if device_raw.get('EPOComputerProperties.OSBitMode', '') == 1 else 32
            device.id = epo_id
            parse_network(device_raw, device, self.logger)
            last_seen = parse_date(device_raw['EPOLeafNode.LastUpdate'])
            if last_seen:
                device.last_seen = last_seen

            device.domain = device_raw.get("EPOComputerProperties.DomainName")
            device.epo_agent_version = device_raw.get("EPOLeafNode.AgentVersion")

            # TODO: Understand if the next line is always included in hostname. Do we need it?
            # device.computer_name = device_raw.get("EPOComputerProperties.ComputerName")

            # The next thing, i'm afraid, could go bad
            try:
                # Set up epo products
                for product in device_raw.get("EPOProductPropertyProducts.Products", "").split(", "):
                    device.epo_products.append(product)

                # Set up os version
                os_version = device_raw.get("EPOComputerProperties.OSVersion")
                if os_version is not None:
                    major, *minor = os_version.split(".")
                    device.os.major = int(major)
                    if len(minor) > 0:
                        device.os.minor = int(minor[0])

                os_build_num = device_raw.get("EPOComputerProperties.OSBuildNum")
                if os_build_num is not None:
                    device.os.build = str(os_build_num)

                # Set up memory
                device.free_physical_memory = int(device_raw.get("EPOComputerProperties.FreeMemory")) / (1024**2)
                device.total_physical_memory = int(device_raw.get(
                    "EPOComputerProperties.TotalPhysicalMemory")) / (1024**2)

                # Set up hard disks
                device.add_hd(
                    total_size=(int(device_raw.get("EPOComputerProperties.TotalDiskSpace")) / 1024),
                    free_size=(int(device_raw.get("EPOComputerProperties.FreeDiskSpace")) / 1024)
                )

                # Set up cpu's
                device.total_number_of_cores = int(device_raw.get("EPOComputerProperties.NumOfCPU"))
                device.add_cpu(
                    speed=round(int(device_raw.get("EPOComputerProperties.CPUSpeed")) / 1024, 2),
                    name=device_raw.get("EPOComputerProperties.CPUType")
                )

            except:
                self.logger.exception("Couldn't set some epo info")

            device.set_raw(device_raw)
            yield device

    def _query_devices_by_client(self, client_name, client_data):
        mc = client(client_data[EPO_HOST], client_data[EPO_PORT],
                    client_data[USER], client_data[PASS])
        table = mc.run("core.listTables", table=LEAF_NODE_TABLE)

        all_linked_tables = get_all_linked_tables(table)

        try:
            # all devices are fetched at once so no progress is logged
            raw = mc.run("core.executeQuery", target=LEAF_NODE_TABLE, joinTables=all_linked_tables)
        except Exception as e:
            try:
                self.logger.warning(f"Failed to query all linked tables - {e}")
                raw = mc.run("core.executeQuery", target=LEAF_NODE_TABLE,
                             joinTables="EPOComputerProperties, EPOProductPropertyProducts")
            except Exception as e:
                self.logger.warning(f"Failed to query EPOComputerProperties, EPOProductPropertyProducts - {e}. \
                                        Will fetch only basic info from EPOComputerProperties")
                raw = mc.run("core.executeQuery", target=LEAF_NODE_TABLE, joinTables="EPOComputerProperties")
        return json.dumps(raw)

    def _get_client_id(self, client_config):
        return client_config[EPO_HOST]

    def _connect_client(self, client_config):
        try:
            client(client_config[EPO_HOST], client_config[EPO_PORT],
                   client_config[USER], client_config[PASS])
        except Exception as e:
            message = "Error connecting to client {0}, reason: {1}".format(self._get_client_id(client_config), str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)
        return client_config

    # Exported API functions - None for now
