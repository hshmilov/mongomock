import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from airwave_adapter.connection import AirwaveConnection
from airwave_adapter.client_id import get_client_id
from airwave_adapter.consts import CLIENT_TYPE, AP_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


class AirwaveAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        airwave_type = Field(str, 'Airwave Device Type', enum=[CLIENT_TYPE, AP_TYPE])
        last_ap = Field(str, 'Last AP')
        role = Field(str, 'Role')
        client_count = Field(int, 'Client Count')
        bandwidth = Field(int, 'Bandwidth')
        ap_type = Field(str, 'AP Type')
        management_state = Field(str, 'Management State')
        monitoring_status = Field(str, 'Monitoring Status')
        controller_id = Field(str, 'Controller ID')
        icmp_address = Field(str, 'ICMP Address')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = AirwaveConnection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       username=client_config['username'],
                                       password=client_config['password'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
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
        The schema AirwaveAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Aruba AirWave Domain',
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
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_client_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            mac = (device_raw.get('mac') or {}).get('value')
            if mac is None:
                logger.warning(f'Bad device with no MAC {device_raw}')
                return None
            device.id = mac
            device.add_nic(mac=mac)
            device.last_seen = parse_date((device_raw.get('connect_time') or {}).get('value'))
            device.role = (device_raw.get('role') or {}).get('value')
            if (device_raw.get('username') or {}).get('value'):
                device.last_used_users = [(device_raw.get('username') or {}).get('value')]
            device.last_ap = (device_raw.get('last_ap_id') or {}).get('value')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Airwave Device for {device_raw}')
            return None

    def _create_ap_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            name = (device_raw.get('name') or {}).get('value')
            if name is None:
                logger.warning(f'Bad device with no Name {device_raw}')
                return None
            device.id = name
            device.name = name
            device.add_nic(mac=name.strip('*'))
            icmp_address = (device_raw.get('icmp_address') or {}).get('value')
            if icmp_address:
                device.icmp_address = icmp_address
                device.add_nic(ips=[icmp_address])
            client_count = (device_raw.get('client_count') or {}).get('value')
            if isinstance(client_count, int):
                device.client_count = client_count

            bandwidth = (device_raw.get('bandwidth') or {}).get('value')
            if isinstance(bandwidth, int):
                device.bandwidth = bandwidth
            device.management_state = (device_raw.get('management_state') or {}).get('value')
            device.ap_type = (device_raw.get('type') or {}).get('value')
            device.monitoring_status = (device_raw.get('monitoring_status') or {}).get('value')
            device.controller_id = (device_raw.get('controller_id') or {}).get('value')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Airwave Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if AP_TYPE == device_type:
                device = self._create_ap_device(device_raw)
            if CLIENT_TYPE == device_type:
                device = self._create_client_device(device_raw)
            if device:
                device.airwave_type = device_type
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
