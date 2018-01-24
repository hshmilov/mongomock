from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.device import Device
from axonius.parsing_utils import format_mac, parse_date, is_valid_ip
import json
import ipaddress
import mcafee

ADMIN_PASS = 'admin_password'
ADMIN_USER = 'admin_user'
EPO_HOST = 'host'
EPO_PORT = 'port'
QUERY_PASS = 'query_password'
QUERY_USER = 'query_user'

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

    device.add_nic(mac, list(ip_list))


class EpoAdapter(AdapterBase):
    """
    Connects axonius to mcafee epo
    """

    class MyDevice(Device):
        pass

    def __init__(self, **kwargs):
        """Class initialization.

        Check AdapterBase documentation for additional params and exception details.

        """

        # Initialize the base plugin (will initialize http server)
        super().__init__(**kwargs)

    def _clients_schema(self):
        return {
            "properties": {
                ADMIN_PASS: {
                    "type": "password"
                },
                ADMIN_USER: {
                    "type": "string"
                },
                EPO_HOST: {
                    "type": "string"
                },
                EPO_PORT: {
                    "type": "integer"
                },
                QUERY_USER: {
                    "type": "string"
                },
                QUERY_PASS: {
                    "type": "password"
                }
            },
            "required": [
                ADMIN_USER,
                ADMIN_USER,
                EPO_PORT,
                EPO_HOST,
                QUERY_PASS,
                QUERY_USER
            ],
            "type": "object"
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

            device.set_raw(device_raw)
            yield device

    def _query_devices_by_client(self, client_name, client_data):
        mc = mcafee.client(client_data[EPO_HOST], client_data[EPO_PORT],
                           client_data[QUERY_USER], client_data[QUERY_PASS])
        table = mc.run("core.listTables", table=LEAF_NODE_TABLE)

        all_linked_tables = get_all_linked_tables(table)

        try:
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
            mcafee.client(client_config[EPO_HOST], client_config[EPO_PORT],
                          client_config[QUERY_USER], client_config[QUERY_PASS])
        except Exception as e:
            message = "Error connecting to client {0}, reason: {1}".format(self._get_client_id(client_config), str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)
        return client_config

    # Exported API functions - None for now
