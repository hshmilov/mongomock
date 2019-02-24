import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from bluecat_adapter.connection import BluecatConnection
from bluecat_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class BluecatAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        device_state = Field(str, 'Device State')
        device_comments = Field(str, 'Device Comments')
        location_code = Field(str, 'Location Code')
        vendor_class_identifier = Field(str, 'Vendor Class Identifier')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with BluecatConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                   username=client_config['username'], password=client_config['password'],
                                   ) as connection:
                return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema BluecatAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Bluecat Domain',
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

    # pylint: disable=R1702,R0912
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if device_id is None:
                    logger.warning(f'Bad device with no id {device_id}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('name') or '')
                device.name = device_raw.get('name').split(',')[0] if device_raw.get('name') else None
                device.hostname = device_raw.get('dns_name')
                device_properties = device_raw.get('properties')
                mac = None
                ips = None
                try:
                    if isinstance(device_properties, str) and device_properties:
                        for property_raw in \
                                [device_property.split('=')
                                 for device_property in device_properties.split('|')[:-1] if '=' in device_property]:
                            if property_raw[0] == 'address':
                                ips = [property_raw[1]]
                            elif property_raw[0] == 'macAddress':
                                mac = property_raw[1]
                            elif property_raw[0] == 'state':
                                device.device_state = property_raw[1]
                            elif property_raw[0] == 'comments':
                                device.device_comments = property_raw[1]
                            elif property_raw[0] == 'locationCode':
                                device.location_code = property_raw[1]
                            elif property_raw[0] == 'vendorClassIdentifier':
                                device.vendor_class_identifier = property_raw[1]
                    if mac or ips:
                        device.add_nic(mac, ips)
                except Exception:
                    logger.exception(f'Problem getting properties for {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Bluecat Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
