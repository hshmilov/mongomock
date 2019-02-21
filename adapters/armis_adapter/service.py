import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from armis_adapter.connection import ArmisConnection
from armis_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ArmisAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        device_category = Field(str, 'Device Category')
        first_seen = Field(datetime.datetime, 'First Seen')
        risk_level = Field(int, 'Risk Level')
        armis_tags = ListField(str, 'Armis Tags')
        device_type = ListField(str, 'Device Type')

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
            with ArmisConnection(domain=client_config['domain'],
                                 verify_ssl=client_config['verify_ssl'],
                                 apikey=client_config['apikey'],
                                 https_proxy=client_config.get('https_proxy')) as connection:
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
        The schema ArmisAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Armis Domain',
                    'type': 'string'
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
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if device_id is None:
                    logger.warning(f'Bad device with no id {device_raw}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('name') or '')
                try:
                    device.last_seen = parse_date(device_raw.get('lastSeen'))
                    device.first_seen = parse_date(device_raw.get('firstSeen'))
                except Exception:
                    logger.exception(f'Problem getting first or last seen for {device_raw}')
                try:
                    ips = device_raw.get('ipAddress').split(',') if device_raw.get('ipAddress') else None
                    mac = device_raw.get('macAddress') if device_raw.get('macAddress') else None
                    if ips or mac:
                        device.add_nic(mac, ips)
                except Exception:
                    logger.exception(f'Problem adding nic to {device_raw}')
                device.device_manufacturer = device_raw.get('manufacturer')
                device.device_model = device_raw.get('model')
                device.hostname = device_raw.get('name')
                device.last_used_users = [device_raw.get('user')] if device_raw.get('user') else None
                device.device_type = device_raw.get('type')
                device.risk_level = device_raw.get('riskLevel')
                try:
                    device.armis_tags = device_raw.get('tags') if isinstance(device_raw.get('tags'), list) else None
                except Exception:
                    logger.exception(f'Problem getting armis tags for {device_raw}')
                device.device_category = device_raw.get('category')
                try:
                    os_str = (device_raw.get('operatingSystem') or '') + ' ' \
                        + (device_raw.get('operatingSystemVersion') or '')
                    device.figure_os(os_str)
                except Exception:
                    logger.exception(f'Problem getting os for {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Armis Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
