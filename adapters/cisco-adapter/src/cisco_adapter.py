from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.device import Device
from cisco_client import CiscoClient

HOST = 'host'
USERNAME = 'username'
PASSWORD = 'password'


class CiscoAdapter(AdapterBase):

    class MyDevice(Device):
        pass

    def _connect_client(self, client_config):
        # tries to connect and throws adapter Exception on failure
        client = CiscoClient(self.logger, host=client_config[HOST], username=client_config[USERNAME],
                             password=client_config[PASSWORD], port=22)
        try:
            client.connect()
        except Exception as e:
            message = "Error connecting to client with {0}: {1}".format(self._get_client_id(client_config), str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)
        finally:
            client.close()
        return client

    def _query_devices_by_client(self, client_name, client_data):
        assert isinstance(client_data, CiscoClient)
        with client_data:
            return list(client_data.get_parsed_arp())

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": HOST,
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": USERNAME,
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                "host",
                "username",
                "password"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._new_device()
            device.id = device_raw['ip']
            device.add_nic(device_raw['mac'], [device_raw['ip']], self.logger)
            device.scanner = True
            device.set_raw(device_raw)
            yield device

    def _get_client_id(self, client_config):
        return client_config[HOST]
