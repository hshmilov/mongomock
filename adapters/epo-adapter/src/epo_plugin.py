from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.parsing_utils import figure_out_os, format_mac
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


def parse_os_details(device_raw_data):
    """
    :param device_raw_data: device raw data as retrieved by query
    :return: parsed os details struct
    """
    details = figure_out_os(device_raw_data.get('EPOLeafNode.os', ''))
    details['bitness'] = 64 if device_raw_data.get('EPOComputerProperties.OSBitMode', '') == 1 else 32
    return details


def parse_network(raw_data):
    mac = format_mac(raw_data['EPOComputerProperties.NetAddress'])
    ipv4 = raw_data['EPOComputerProperties.IPV4x']

    # epo is a motherfucker? Seems like he loves to flip the msb of the binary repr of ip addr...
    ipv4 = (ipv4 & 0xffffffff) ^ 0x80000000

    # to string
    ipv4 = str(ipaddress.IPv4Address(ipv4))

    ipv6 = raw_data['EPOComputerProperties.IPV6'].lower()
    res = dict()
    res['MAC'] = mac
    res['IP'] = [ipv4, ipv6]
    return [res]


class EpoPlugin(AdapterBase):
    """
    Connects axonius to mcafee epo
    """

    def __init__(self, **kargs):
        """Class initialization.

        Check AdapterBase documentation for additional params and exception details.

        """

        # Initialize the base plugin (will initialize http server)
        super().__init__(**kargs)

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
            yield {
                'hostname': device_raw_data.get('EPOComputerProperties.IPHostName',
                                                device_raw_data.get('EPOComputerProperties.ComputerName', '')),
                'OS': parse_os_details(device_raw_data),
                'id': device_raw_data['EPOLeafNode.AgentGUID'],
                'network_interfaces': parse_network(device_raw_data),
                'raw': json.dumps(device_raw_data)}

    def _query_devices_by_client(self, client_name, client_data):
        mc = mcafee.client(client_data[EPO_HOST], client_data[EPO_PORT],
                           client_data[QUERY_USER], client_data[QUERY_PASS])
        table = mc.run("core.listTables", table=LEAF_NODE_TABLE)

        all_linked_tables = get_all_linked_tables(table)
        raw = mc.run("core.executeQuery", target=LEAF_NODE_TABLE,
                     joinTables=all_linked_tables)
        return json.dumps(raw)

    def _get_client_id(self, client_config):
        return client_config[EPO_HOST]

    def _connect_client(self, client_config):
        try:
            mcafee.client(client_config[EPO_HOST], client_config[EPO_PORT],
                          client_config[QUERY_USER], client_config[QUERY_PASS])
        except Exception as e:
            message = "Error connecting to client {0}, reason: {1}".format(self._get_client_id(client_config), str(e))
            self.logger.error(message)
            raise ClientConnectionException(message)
        return client_config

    # Exported API functions - None for now
