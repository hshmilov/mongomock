from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import AdapterException
from axonius.consts.adapter_consts import SCANNER_FIELD
from cisco_client import CiscoClient

HOST = 'host'
USERNAME = 'username'
PASSWORD = 'password'


class CiscoAdapter(AdapterBase):
    def _connect_client(self, client_config):
        # tries to connect and throws adapter Exception on failure
        return CiscoClient(self.logger, host=client_config[HOST], username=client_config[USERNAME],
                           password=client_config[PASSWORD], port=22)

    def _query_devices_by_client(self, client_name, client_data):
        assert isinstance(client_data, CiscoClient)
        client_data.connect()  # refresh connection
        return client_data.get_parsed_arp()

    def _clients_schema(self):
        return {
            "properties": {
                HOST: {
                    "type": "string",
                    "name": "Host"
                },
                USERNAME: {
                    "type": "string",
                    "name": "Username"
                },
                PASSWORD: {
                    "type": "password",
                    "name": "Password"
                }
            },
            "required": [
                "host",
                "username",
                "password"
            ],
            "type": "object"
        }

    def _parse_raw_data(self, raw_data):
        for entry in raw_data:
            yield {
                'id': entry["IP"],
                'network_interfaces': [{'MAC': entry['MAC'], 'IP': [entry['IP']]}],
                SCANNER_FIELD: True,
                'raw': entry
            }

    def _get_client_id(self, client_config):
        return client_config[HOST]
