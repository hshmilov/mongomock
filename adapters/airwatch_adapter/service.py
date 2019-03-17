import logging

from airwatch_adapter.connection import AirwatchConnection
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class AirwatchAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        imei = Field(str, 'IMEI')
        phone_number = Field(str, 'Phone Number')
        udid = Field(str, 'UdId')
        email = Field(str, 'Email')
        friendly_name = Field(str, 'Friendly Name')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = AirwatchConnection(domain=client_config['domain'],
                                            apikey=client_config['apikey'], verify_ssl=client_config['verify_ssl'],
                                            https_proxy=client_config.get('https_proxy'),
                                            username=client_config['username'],
                                            password=client_config['password'], url_base_prefix='/api/',
                                            headers={'User-Agent': 'Fiddler',
                                                     'aw-tenant-code': client_config['apikey'],
                                                     'Accept': 'application/xml'})
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Airwatch domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Airwatch connection

        :return: A json with all the attributes returned from the Airwatch Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema AirwatchAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Airwatch Domain',
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
                    'name': 'apikey',
                    'title': 'API Key',
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
                    'title': 'Https Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912,R0915
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                if not device_raw.get('Id'):
                    continue
                else:
                    device.id = str(device_raw.get('Id').get('Value'))
                device.imei = device_raw.get('Imei')
                device.last_seen = parse_date(str(device_raw.get('LastSeen', '')))
                device.figure_os((device_raw.get('Platform') or '') + ' ' + (device_raw.get('OperatingSystem') or ''))
                device.phone_number = device_raw.get('PhoneNumber')
                device.email = device_raw.get('UserEmailAddress')
                try:
                    network_raw = device_raw.get('Network') or {}
                    wifi_info = network_raw.get('WifiInfo') or {}
                    mac_address = wifi_info.get('WifiMacAddress', device_raw.get('MacAddress'))
                    if not mac_address or mac_address == '0.0.0.0':
                        mac_address = None
                    ipaddresses_raw = network_raw.get('IPAddress') or []
                    ipaddresses = []
                    falsed_ips = ['0.0.0.0', '127.0.0.1', '', None]
                    for ipaddress_raw in ipaddresses_raw:
                        if ipaddresses_raw[ipaddress_raw] not in falsed_ips:
                            ipaddresses.append(ipaddresses_raw[ipaddress_raw])
                    if ipaddresses != [] or mac_address is not None:
                        device.add_nic(mac_address, ipaddresses)
                except Exception:
                    logger.exception('Problem adding nic to Airwatch')
                device.device_serial = device_raw.get('SerialNumber')
                device.udid = device_raw.get('Udid')

                name = device_raw.get('DeviceFriendlyName')
                username = device_raw.get('UserName')
                if username and name and name.startswith(username + ' '):
                    name = name[len(username) + 1:]
                    if ' Desktop Windows ' in name:
                        name = name[:name.index(' Desktop Windows ')]
                    if ' MacBook Pro ' in name:
                        name = name[:name.index(' MacBook Pro ')]
                    if ' iPhone iOS ' in name:
                        name = name[:name.index(' iPhone iOS ')]
                        if ' Android ' in name:
                            name = name[:name.index(' Android ')]
                    name = name.replace(' ', '-')
                    name = name.replace('\'', '')
                    name = name.replace('’', '')
                    name = name.replace('(', '')
                    name = name.replace(')', '')
                    name = name.replace('.', '-')
                device.name = name + '_' + str(device_raw.get('MacAddress'))
                device.friendly_name = device_raw.get('DeviceFriendlyName')

                device.last_used_users = (device_raw.get('UserName') or '').split(',')
                try:
                    for app_raw in device_raw.get('DeviceApps', []):
                        device.add_installed_software(name=app_raw.get('ApplicationName'),
                                                      version=app_raw.get('Version'))
                except Exception:
                    logger.exception(f'Problem adding software to Airwatch {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Airwatch Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.MDM]
