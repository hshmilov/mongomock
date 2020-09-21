import logging

from axonius.clients.cisco import console
from axonius.clients.cisco import snmp
from axonius.clients.cisco import constants
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.mixins.configurable import Configurable
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.cisco.abstract import CiscoDevice, InstanceParser
from axonius.multiprocess.multiprocess import concurrent_multiprocess_yield
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from cisco_adapter.parse import query_devices_by_client_cisco, prepare_for_parse_raw_data_cisco

logger = logging.getLogger(f'axonius.{__name__}')


PROTOCOLS = {
    'snmp': (snmp.CiscoSnmpClient, 161),
    'snmpv3': (snmp.CiscoSnmpV3Client, 161),
    'ssh': (console.CiscoSshClient, 22),
    'telnet': (console.CiscoTelnetClient, 23),
}
DEFAULT_PROTOCOL = 'snmp'


def outside_query_devices_by_client(client_name, client_data):
    for device in client_data.query_all():
        yield client_name, 'devices', device


class CiscoAdapter(AdapterBase, Configurable):
    MyDeviceAdapter = CiscoDevice

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _connect_client(self, client_config):
        # tries to connect and throws adapter Exception on failure
        try:
            cls, _ = PROTOCOLS[client_config['protocol']]
            client = cls(**client_config)
            client.validate_connection()
            return client
        except Exception as e:
            message = 'Error connecting to client with {0}: {1}'.format(
                self._get_client_id(client_config), get_exception_string())
            logger.exception(message)
            raise ClientConnectionException(str(e))

    @staticmethod
    def _query_devices_by_client_parallel():
        return outside_query_devices_by_client

    def _query_devices_by_client(self, client_name, client_data):
        _ = (yield from concurrent_multiprocess_yield(
            [
                (
                    query_devices_by_client_cisco,
                    (
                        client_data,
                    ),
                    {}
                )
            ],
            1
        ))

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'host',
                    'title': 'Host Name',
                    'type': 'string'
                },
                {
                    'name': 'protocol',
                    'title': 'Protocol',
                    'type': 'string',
                    'enum': list(PROTOCOLS.keys()),
                    'default': DEFAULT_PROTOCOL
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string',
                    'description': 'Console user name for Telnet/SSH'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password',
                    'description': 'Console password for Telnet/SSH'
                },
                {
                    'name': 'community',
                    'title': 'SNMP Read Community',
                    'type': 'string',
                    'format': 'password',
                },
                {
                    'name': 'auth_passphrase',
                    'title': 'SNMPv3 Authentication Passphrase (authKey)',
                    'type': 'string',
                    'format': 'password',
                },
                {
                    'name': 'priv_passphrase',
                    'title': 'SNMPv3 Private Passphrase (privKey)',
                    'type': 'string',
                    'format': 'password',
                },
                {
                    'name': 'auth_protocol',
                    'title': 'SNMPv3 Authentication Type (authProtocol)',
                    'type': 'string',
                    'enum': list(constants.AUTH_PROTOCOLS._fields),
                    'default': 'hmac_md5'
                },
                {
                    'name': 'priv_protocol',
                    'title': 'SNMPv3 Privacy Type (privProtocol)',
                    'type': 'string',
                    'enum': list(constants.PRIV_PROTOCOLS._fields),
                    'default': 'aescfb128',
                },
                {
                    'name': 'secure_level',
                    'title': 'SNMPv3 Security Level (level)',
                    'type': 'string',
                    'enum': list(constants.SECURITY_LEVELS),
                    'default': 'authPriv',
                },

                {
                    'name': 'port',
                    'title': 'Protocol Port',
                    'type': 'integer',
                    'description': 'Protocol Port (Default: standard port)'
                },
                {
                    'name': 'description',
                    'title': 'Description',
                    'type': 'string',
                },

            ],
            'required': [
                'host',
                'protocol'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        yield from self.__parse_raw_data(prepare_for_parse_raw_data_cisco(devices_raw_data))

    def __parse_raw_data(self, devices_raw_data):
        for device in InstanceParser(devices_raw_data).get_devices(self._new_device_adapter):
            try:
                if not self.__fetch_arp and device.fetch_proto == 'ARP':
                    continue
                yield device
            except Exception:
                pass

    @staticmethod
    def _prepare_client_config(client_config):
        # XXX: require and default doesn't so we must hack the protocol here
        if client_config.get('protocol') not in PROTOCOLS:
            client_config['protocol'] = 'snmp'

        _, default_port = PROTOCOLS[client_config['protocol']]

        # we use if not so '' and 0 and None will get default port
        if not client_config.get('port'):
            client_config['port'] = default_port

        if not client_config.get('auth_passphrase'):
            client_config['auth_passphrase'] = None

        if not client_config.get('priv_passphrase'):
            client_config['priv_passphrase'] = None

        return client_config

    def _get_client_id(self, client_config):
        client_config = self._prepare_client_config(client_config)
        return client_config['host']

    def _test_reachability(self, client_config):
        client_config = self._prepare_client_config(client_config)
        client, _ = PROTOCOLS[client_config['protocol']]
        return client.test_reachability(client_config['host'], client_config['port'])

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_arp',
                    'title': 'Fetch ARP data',
                    'type': 'bool'
                }
            ],
            'required': [
                'fetch_arp',
            ],
            'pretty_name': 'Cisco Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_arp': True
        }

    def _on_config_update(self, config):
        self.__fetch_arp = config['fetch_arp']
