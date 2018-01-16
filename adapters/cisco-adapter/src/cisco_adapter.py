from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import AdapterException
from cisco_client import CiscoClient

HOST = 'host'
PORT = 'port'
USERNAME = 'username'
PASSWORD = 'password'
VERIFY_SSL = 'verify_ssl'


class CiscoAdapter(AdapterBase):
    def _connect_client(self, client_config):
        # tries to connect and throws adapter Exception on failure
        return CiscoClient(self.logger, host=client_config[HOST], username=client_config[USERNAME],
                           password=client_config[PASSWORD], port=client_config.get(PORT, 22))

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
                PORT: {
                    "type": "integer",
                    "name": "Port"
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
                'raw': entry
            }

    def _get_client_id(self, client_config):
        return f"{client_config[HOST]}:{client_config.get(PORT, 22)}"
