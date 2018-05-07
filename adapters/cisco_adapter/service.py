import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string

import axonius.clients.cisco.ssh as ssh
import axonius.clients.cisco.snmp as snmp
from axonius.clients.cisco.abstract import InstanceParser, CiscoDevice


class CiscoAdapter(AdapterBase):
    MyDeviceAdapter = CiscoDevice

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _has_snmp_creds(client_config):
        return all(map(client_config.get, ('snmp_community', 'snmp_port')))

    @staticmethod
    def _has_ssh_creds(client_config):
        return all(map(client_config.get, ('ssh_username', 'ssh_password', 'ssh_port')))

    def _get_client(self, client_config):
        '''
        validate that we have all the needed config in client_config,
        and choose which client we should use.
        for now we prefer snmp client.
        maybe we should try both ssh and snmp, maybe even correlate between them?
        '''

        if self._has_snmp_creds(client_config):
            logger.info('using snmp')
            return snmp.CiscoSnmpClient(ip=client_config['host'],
                                        community=client_config['snmp_community'], port=client_config['snmp_port'])

        if self._has_ssh_creds(client_config):
            logger.info('using ssh')
            return ssh.CiscoSshClient(host=client_config['host'], username=client_config['ssh_username'],
                                      password=client_config['ssh_password'], port=client_config['ssh_port'])

        raise ClientConnectionException('client_config doesn\'t have any support client')

    def _connect_client(self, client_config):
        # tries to connect and throws adapter Exception on failure
        try:

            # use 'with' to check that connection works
            with self._get_client(client_config) as client:
                return client
        except Exception as e:
            message = "Error connecting to client with {0}: {1}".format(
                self._get_client_id(client_config), get_exception_string())
            logger.exception(message)
            raise

    def _query_devices_by_client(self, client_name, client_data):
        assert isinstance(client_data, ssh.CiscoSshClient) or isinstance(client_data, snmp.CiscoSnmpClient), client_data
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
                    "name": 'ssh_username',
                    "title": 'User Name',
                    "type": 'string'
                },
                {
                    "name": 'ssh_password',
                    "title": "Password",
                    "type": 'string',
                    "format": 'password'
                },
                {
                    "name": 'ssh_port',
                    "title": 'Ssh port',
                    "type": 'integer',
                    "description": "ssh port (Default: 22)"
                },
                {
                    "name": 'snmp_community',
                    "title": 'Snmp read community',
                    "type": 'string',
                    "format": 'password'
                },
                {
                    "name": 'snmp_port',
                    "title": 'Snmp port',
                    "type": 'integer',
                    "description": 'snmp port (Default: 161)'
                }

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
        client_config.setdefault('ssh_port', 22)
        client_config.setdefault('snmp_port', 161)

        return client_config['host']

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
