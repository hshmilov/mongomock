
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from zabbix_adapter.connection import ZabbixConnection

logger = logging.getLogger(f'axonius.{__name__}')


class ZabbixAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['domain'] + '_' + client_config['username']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = ZabbixConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          username=client_config['username'],
                                          password=client_config['password'],
                                          url_base_prefix=client_config['default_path'],
                                          https_proxy=client_config.get('https_proxy'))
            with connection:
                pass
            return connection
        except Exception as e:
            # pylint: disable=W1202
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Zabbix Domain',
                    'type': 'string'
                },
                {
                    'name': 'default_path',
                    'title': 'Default Zabbix Url Path',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'default_path',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def create_device(self, device_raw):
        device = self._new_device_adapter()
        device_id = device_raw.get('hostid')
        if not device_id:
            logger.exception(f'Device with no ID {device_raw}')
            return None
        device.name = device_raw.get('name')
        device.description = device_raw.get('description')
        # Waiting for field test to understand this field
        #device.hostname = device_raw.get('host')
        try:
            os = (device_raw.get('inventory') or {}).get('os')
            if os:
                device.figure_os(os)
        except Exception:
            logging.exception(f'Problem getting os at {device_raw}')
        try:
            interfaces = device_raw.get('interfaces') or []
            ips = []
            for interface in interfaces:
                ip = interface.get('ip')
                if ip:
                    ips.append(ip)
            if ips:
                device.add_nic(None, ips)
        except Exception:
            logger.exception(f'Problem adding nic to {device_raw}')
        device.id = device_id + '_' + (device_raw.get('name') or '')
        device.set_raw(device_raw)

        return device

    def _parse_raw_data(self, devices_raw_data):
        for raw_device_data in iter(devices_raw_data):
            try:
                device = self.create_device(raw_device_data)
                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
