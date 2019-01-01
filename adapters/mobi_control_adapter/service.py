import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.parsing import parse_date
from mobi_control_adapter.connection import MobiControlConnection
from mobi_control_adapter.client_id import get_client_id


logger = logging.getLogger(f'axonius.{__name__}')


class MobiControlAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        is_online = Field(bool, 'Is Online')
        agent_version = Field(str, 'Agent Version')
        cell_carrier = Field(str, 'Cell Carrier')
        imei = Field(str, 'IMEI')
        in_roaming = Field(bool, 'In Roaming')
        network_bssid = Field(str, 'Network BSSID')
        phone_number = Field(str, 'Phone Number')

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
            connection = MobiControlConnection(domain=client_config['domain'],
                                               verify_ssl=client_config['verify_ssl'],
                                               username=client_config['username'],
                                               password=client_config['password'],
                                               https_proxy=client_config.get('https_proxy'),
                                               client_id=client_config['client_id'],
                                               client_secret=client_config['client_secret'])
            with connection:
                pass
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
        The schema MobiControlAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'MobiControl Domain',
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
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
                    'title': 'Client Secret',
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
                'client_id',
                'client_secret',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('DeviceId')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = device_id + '_' + (device_raw.get('HostName') or '')
                device.hostname = device_raw.get('HostName')
                device.is_online = device_raw.get('IsAgentOnline')
                device.name = device_raw.get('DeviceName')
                try:
                    mac_wifi = device_raw.get('MACAddress')
                    ips = [device_raw.get('Ipv6')] if device_raw.get('Ipv6') else None
                    if not mac_wifi:
                        mac_wifi = None
                    if mac_wifi or ips:
                        device.add_nic(mac_wifi, ips)
                except Exception:
                    logger.exception(f'Problem adding MAC Wifi to {device_raw}')
                device.agent_version = device_raw.get('AgentVersion')
                device.in_romaing = device_raw.get('InRoaming')
                try:
                    device.last_seen = parse_date(device_raw.get('LastCheckInTime'))
                except Exception:
                    logger.exception(f'Problem adding last seen to {device_raw}')
                device.cell_carrier = device_raw.get('CellularCarrier')
                device.imei = device_raw.get('IMEI_MEID_ESN')
                device.network_bssid = device_raw.get('NetworkBSSID')
                try:
                    if device_raw.get('LastLoggedOnUser'):
                        device.last_used_users = [device_raw.get('LastLoggedOnUser')]
                except Exception:
                    logger.exception(f'Problem getting last used user {device_raw}')
                device.phone_number = device_raw.get('PhoneNumber')

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching MobiControl Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
