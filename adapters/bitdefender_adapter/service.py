import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from bitdefender_adapter.connection import BitdefenderConnection

logger = logging.getLogger(f'axonius.{__name__}')


class BitdefenderAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        is_managed = Field(bool, 'Is Managed')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = BitdefenderConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                               username=client_config['apikey'],
                                               https_proxy=client_config.get('https_proxy'))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema the adapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Bitdefender Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string'
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
                'apikey',
                'veirfy_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if not device_id:
                    logger.warning(f'Device with no ID {device_raw}')
                    continue
                device_id += device_raw.get('name') or ''
                device.id = device_id
                device.name = device_raw.get('name')
                device.hostname = device_raw.get('fqdn')
                device.figure_os(device_raw.get('operatingSystemVersion'))
                try:
                    ip_address = device_raw.get('ip') or []
                    if ip_address:
                        ip_address = ip_address.split(',')
                    mac_addresses = device_raw.get('macs') or []
                    device.add_ips_and_macs(mac_addresses, ip_address)
                except Exception:
                    logger.exception(f'Problem adding nic to {device_raw}')
                is_managed = device_raw.get('isManaged')
                if is_managed and isinstance(is_managed, bool):
                    device.is_managed = is_managed
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Bitdefender Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
