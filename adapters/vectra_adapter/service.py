import logging

from axonius.utils.parsing import parse_date
from axonius.utils.files import get_local_config_file
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from vectra_adapter.client_id import get_client_id
from vectra_adapter.structures import VectraInstance
from vectra_adapter.connection import VectraConnection

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class VectraAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(VectraInstance):
        pass

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
        connection = VectraConnection(domain=client_config['domain'],
                                      token=client_config['token'],
                                      verify_ssl=client_config.get('verify_ssl') or False)
        with connection:
            pass  # check the connection credentials are valid
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
        The schema VectraAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Vectra Domain',
                    'type': 'string'
                },
                {
                    'name': 'token',
                    'title': 'API Token',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool',
                },
            ],
            'required': [
                'domain',
                'token'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_vectra_fields(device_raw, device_instance: MyDeviceAdapter):
        try:
            device_instance.c_score = device_raw.get('c_score')
            device_instance.c_score_gte = device_raw.get('c_score_gte')
            device_instance.fields = device_raw.get('fields')
            device_instance.key_asset = device_raw.get('key_asset')
            device_instance.last_detection_timestamp = parse_date(device_raw.get('last_detection_timestamp'))
            device_instance.ordering = device_raw.get('ordering')
            device_instance.page = device_raw.get('page')
            device_instance.page_size = device_raw.get('page_size')
            device_instance.state = device_raw.get('state')
            device_instance.t_score = device_raw.get('t_score')
            device_instance.t_score_gte = device_raw.get('t_score_gte')
        except Exception:
            logger.exception(f'Failed to parse Vectra instance info for device {device_raw}')

    def _create_device(self, device_raw, device: MyDeviceAdapter):
        try:

            device_id = (device_raw.get('mac_address') or '') + (device_raw.get('last_source') or '')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id

            device.add_ips_and_macs(macs=[device_raw.get('mac_address')],
                                    ips=[device_raw.get('last_source')])

            self._fill_vectra_fields(device_raw, device)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Vectra Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Vectra Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
