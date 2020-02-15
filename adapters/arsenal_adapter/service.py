import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.fields import Field, ListField
from axonius.utils.dynamic_fields import put_dynamic_field
from arsenal_adapter.connection import ArsenalConnection
from arsenal_adapter.client_id import get_client_id
from arsenal_adapter.consts import ALLOWED_TYPES

logger = logging.getLogger(f'axonius.{__name__}')


class ArsenalAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        asset_type = Field(str, 'Asset Type')
        hostnames = ListField(str, 'Hostnames')
        last_modified_date = Field(datetime.datetime, 'Last Modified Date')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = ArsenalConnection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'))
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
        The schema ArsenalAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Arsenal Domain',
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements
    def _create_device(self, device_raw):
        try:
            if device_raw.get('type') not in ALLOWED_TYPES:
                return None
            device = self._new_device_adapter()
            device_id = device_raw.get('id').get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('serialNumber') or '')
            device.device_serial = device_raw.get('serialNumber')
            device.asset_type = device_raw.get('type')
            try:
                ips_opinions_raw = (device_raw.get('ips') or {}).get('opinions') or {}
                for ips_values_raw in ips_opinions_raw.values():
                    if ips_values_raw.get('values'):
                        device.add_nic(ips=ips_values_raw.get('values'))
            except Exception:
                logger.exception(f'Problem getting ips for {device_raw}')
            hostname = None
            try:
                hostnames_opinions_raw = (device_raw.get('hostNames') or {}).get('opinions') or {}
                for hostname_values_raw in hostnames_opinions_raw.values():
                    if hostname_values_raw.get('values'):
                        hostname = hostname_values_raw.get('values')[0]
                        device.hostnames.extend(
                            [hostname_raw for hostname_raw in hostname_values_raw.get('values') if hostname_raw])
            except Exception:
                logger.exception(f'Problem getting hostnames for {device_raw}')

            if hostname:
                device.hostname = hostname
            else:
                device.name = device_raw.get('serialNumber')

            device.last_modified_date = parse_date(device_raw.get('lastModifiedDate'))

            for key, value in device_raw.items():
                try:
                    put_dynamic_field(device, f'arsenal_{key}', value, f'arsenal.{key}')
                except Exception:
                    logger.exception(f'Failed putting key {key} with value {value}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Arsenal Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
