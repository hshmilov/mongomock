import logging
import ipaddress

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from cynet_adapter.connection import CynetConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CynetAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = CynetConnection(domain=client_config['domain'],
                                         username=client_config['username'],
                                         password=client_config['password'],
                                         verify_ssl=client_config.get('verify_ssl', False),
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
        Get all devices from a specific cynet domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a cynet connection

        :return: A json with all the attributes returned from the cynet Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema cynetAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cynet Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'Username',
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
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                hostname = device_raw.get('hostName')
                # Ofri saw wierd entities with no hostname and IDs. These are not real devices.
                if not device_id or not hostname:
                    logger.warning(f'No id of device {device_raw}')
                    continue
                device.id = device_id + (hostname or '')
                device.hostname = hostname
                device.last_seen = parse_date(device_raw.get('lastScan'))
                try:
                    ip = device_raw.get('lastIP')
                    if ip:
                        device.add_nic(None, [str(ipaddress.ip_address(int(ip)))])
                except Exception:
                    logger.exception(f'Problem getting IP for cynet device {device_raw}')
                device.figure_os(device_raw.get('osVersion'))

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Cynet Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
