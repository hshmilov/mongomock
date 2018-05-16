import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string

import axonius.clients.cisco.console as console
import axonius.clients.cisco.snmp as snmp
from axonius.clients.cisco.abstract import InstanceParser, CiscoDevice


PROTOCOLS = {
    'snmp': (snmp.CiscoSnmpClient, 161),
    'ssh': (console.CiscoSshClient, 22),
    'telnet': (console.CiscoTelnetClient, 23),
}


class CiscoAdapter(AdapterBase):
    MyDeviceAdapter = CiscoDevice

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _connect_client(self, client_config):
        # tries to connect and throws adapter Exception on failure
        try:
            # use 'with' to check that connection works
            cls, _ = PROTOCOLS[client_config['protocol']]
            with cls(**client_config) as client:
                return client
        except Exception as e:
            message = "Error connecting to client with {0}: {1}".format(
                self._get_client_id(client_config), get_exception_string())
            logger.exception(message)
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            # Returns objects that can later return devices using .get_devices() method (see abstract.py)
            yield from client_data.query_all()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": 'host',
                    "title": 'Host Name',
                    "type": 'string'
                },
                {
                    "name": 'protocol',
                    "title": 'Protocol to use',
                    "type": 'string',
                    "enum": list(PROTOCOLS.keys()),
                },
                {
                    "name": 'username',
                    "title": 'User Name',
                    "type": 'string',
                    "description": "Console username for telnet/ssh"
                },
                {
                    "name": 'password',
                    "title": "Password",
                    "type": 'string',
                    "format": 'password',
                    "description": "Console password for telnet/ssh"
                },
                {
                    "name": 'community',
                    "title": 'Snmp read community',
                    "type": 'string',
                    "format": 'password',
                },
                {
                    "name": 'port',
                    "title": 'Protocol port',
                    "type": 'integer',
                    "description": "Protocol Port (Default: standart port)"
                },

            ],
            "required": [
                "host",
            ],
            "type": "array"
        }

    def _parse_raw_data(self, instances):
        return InstanceParser(instances).get_devices(self._new_device_adapter)

    def _get_client_id(self, client_config):
        # TODO: is there a better place to set default values for client_config?
        _, default_port = PROTOCOLS[client_config['protocol']]
        client_config.setdefault('port', default_port)

        return client_config['host']

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
