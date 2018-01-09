from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.parsing_utils import format_mac, parse_date
from axonius.parsing_utils import figure_out_os
from axonius.consts import adapter_consts
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
IP_ADDR = 'IP'


def get_all_linked_tables(table):
    """
    :param table: table data
    :return: list of tables linked by a foreign key
    """
    by_lines = table['foreignKeys'].strip().split("\n")[2:]
    foreign_tables = [line.split()[2] for line in by_lines]
    all_linked_tables = ",".join(foreign_tables)
    return all_linked_tables


def parse_os_details(device_raw_data):
    """
    :param device_raw_data: device raw data as retrieved by query
    :return: parsed os details struct
    """
    details = figure_out_os(device_raw_data.get('EPOLeafNode.os', ''))
    details['bitness'] = 64 if device_raw_data.get('EPOComputerProperties.OSBitMode', '') == 1 else 32
    return details


def parse_network(raw_data, logger):
    res = dict()
    res[IP_ADDR] = []

    raw_ipv4 = raw_data.get('EPOComputerProperties.IPV4x')
    parsed_ipv4 = None
    try:
        # epo is a motherfucker? Seems like he flips the msb of the binary repr of ip addr...
        ipv4 = (raw_ipv4 & 0xffffffff) ^ 0x80000000
        parsed_ipv4 = str(ipaddress.IPv4Address(ipv4))
        res[IP_ADDR].append(parsed_ipv4)
    except:
        logger.info(f"Error reading IPv4 {raw_ipv4}")

    raw_ipv6 = raw_data.get('EPOComputerProperties.IPV6').lower()
    res[IP_ADDR].append(raw_ipv6)

    ipv4mapped = ipaddress.IPv6Address(raw_ipv6).ipv4_mapped
    if str(ipv4mapped) != parsed_ipv4:
        logger.info(f"ipv4/6 mismatch: raw4={raw_ipv4} raw6={raw_ipv6} parsed4={parsed_ipv4} ip4-6mapped={ipv4mapped}")
        if ipv4mapped:
            # epo's ipv4 reporting is problematic.
            # But we noticed that mapped ipv6 addresses tend to have the correct value
            # In such a case we add the mapped ipv4 address
            res[IP_ADDR].append(str(ipv4mapped))

    raw_mac = raw_data.get('EPOComputerProperties.NetAddress')
    try:
        mac = format_mac(raw_mac)
        res['MAC'] = mac
    except:
        logger.info(f"Failed formatting {raw_mac}")

    # unique
    res[IP_ADDR] = list(set(res[IP_ADDR]))
    return [res]


class EpoAdapter(AdapterBase):
    """
    Connects axonius to mcafee epo
    """

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

    def _parse_raw_data(self, raw_data):
        raw_data = json.loads(raw_data)
        for device_raw_data in raw_data:
            epo_id = device_raw_data.get('EPOLeafNode.AgentGUID')

            if epo_id is None:
                self.logger.error(f"Got epo device without EPOLeafNode.AgentGUID {device_raw_data}")

            parsed = {
                'hostname': device_raw_data.get('EPOComputerProperties.IPHostName',
                                                device_raw_data.get('EPOComputerProperties.ComputerName', '')),
                'OS': parse_os_details(device_raw_data),
                'id': epo_id,
                'network_interfaces': parse_network(device_raw_data, self.logger),
                'raw': device_raw_data}

            last_seen = parse_date(device_raw_data['EPOLeafNode.LastUpdate'])
            if last_seen:
                parsed[adapter_consts.LAST_SEEN_PARSED_FIELD] = last_seen

            yield parsed

    def _query_devices_by_client(self, client_name, client_data):
        mc = mcafee.client(client_data[EPO_HOST], client_data[EPO_PORT],
                           client_data[QUERY_USER], client_data[QUERY_PASS])
        table = mc.run("core.listTables", table=LEAF_NODE_TABLE)

        all_linked_tables = get_all_linked_tables(table)

        raw = dict()
        try:
            raw = mc.run("core.executeQuery", target=LEAF_NODE_TABLE, joinTables=all_linked_tables)
        except Exception as e:
            self.logger.warn(f"Failed to query all linked tables - {e}")
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
