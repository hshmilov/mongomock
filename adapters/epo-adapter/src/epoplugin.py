from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os

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
    details = figure_out_os(device_raw_data['EPOLeafNode.os'])
    details['bitness'] = 64 if device_raw_data['EPOComputerProperties.OSBitMode'] == 1 else 32
    return details


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
                    "type": "string"
                },
                ADMIN_USER: {
                    "type": "string"
                },
                EPO_HOST: {
                    "type": "string"
                },
                EPO_PORT: {
                    "type": "string"
                },
                QUERY_USER: {
                    "type": "string"
                },
                QUERY_PASS: {
                    "type": "string"
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
        for device_raw_data in raw_data:
            yield {
                'name': device_raw_data['EPOComputerProperties.ComputerName'],
                'os': figure_out_os(parse_os_details(device_raw_data)),
                'id': device_raw_data['EPOLeafNode.AgentGUID'],
                'raw': device_raw_data}

    def _query_devices_by_client(self, client_name, client_data):
        host = client_data[EPO_HOST]
        port = client_data[EPO_PORT]
        user = client_data[QUERY_USER]
        passw = client_data[QUERY_PASS]

        mc = mcafee.client(host, port, user, passw)
        table = mc.run("core.listTables", table=LEAF_NODE_TABLE)

        all_linked_tables = get_all_linked_tables(table)
        return mc.run("core.executeQuery", target=LEAF_NODE_TABLE, joinTables=all_linked_tables)

    def _parse_clients_data(self, clients_config):
        return clients_config  # no need to parse anything...
