import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.uptycs.connection import UptycsConnection
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from uptycs_adapter.client_id import get_client_id
from uptycs_adapter.structures import UptycsDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class UptycsAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(UptycsDeviceInstance):
        pass

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
        connection = UptycsConnection(domain=client_config.get('domain'),
                                      verify_ssl=client_config.get('verify_ssl'),
                                      https_proxy=client_config.get('https_proxy'),
                                      proxy_username=client_config.get('proxy_username'),
                                      proxy_password=client_config.get('proxy_password'),
                                      apikey=client_config.get('apikey'),
                                      apisecret=client_config.get('apisecret'),
                                      customer_id=client_config['customer_id'])
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema UptycsAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'customer_id',
                    'title': 'Customer ID',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string'
                },
                {
                    'name': 'apisecret',
                    'title': 'API Secret',
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
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'apikey',
                'apisecret',
                'customer_id',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_uptycs_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.location = device_raw.get('location')
            device.device_status = device_raw.get('status')
            device.os_query_version = device_raw.get('osqueryVersion')
            device.uptated_by = device_raw.get('updatedBy')
            device.last_enrolled_at = parse_date(device_raw.get('lastEnrolledAt'))
            device.live = parse_bool_from_raw(device_raw.get('live'))
            device.deleted_at = parse_date(device_raw.get('deletedAt'))
            device.config_id = device_raw.get('configId')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('hostName') or '')
            device.first_seen = parse_date(device_raw.get('createdAt'))
            device.hostname = device_raw.get('hostName')
            device.device_disabled = parse_bool_from_raw(device_raw.get('disabled'))
            device.description = device_raw.get('description')
            device.total_number_of_cores = int_or_none(device_raw.get('cores'))
            device.device_manufacturer = device_raw.get('hardwareVendor')
            device.last_seen = parse_date(device_raw.get('lastActivityAt'))
            device.figure_os((device_raw.get('os') or '') + ' ' + (device_raw.get('osVersion') or '')
                             + ' ' + (device_raw.get('osFlavor') or ''))
            tags_raw = device_raw.get('tags')
            if not isinstance(tags_raw, list):
                tags_raw = []
            for tag_raw in tags_raw:
                if not isinstance(tag_raw, str):
                    continue
                if '=' in tag_raw:
                    tag_name = tag_raw.split('=')[0]
                    tag_value = tag_raw.split('=')[1]
                else:
                    tag_name = tag_raw
                    tag_value = None
                device.add_key_value_tag(key=tag_name, value=tag_value)
            self._fill_uptycs_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Uptycs Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Uptycs Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
