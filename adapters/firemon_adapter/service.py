import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from firemon_adapter import consts
from firemon_adapter.connection import FiremonConnection
from firemon_adapter.client_id import get_client_id
from firemon_adapter.structures import FiremonDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class FiremonAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(FiremonDeviceInstance):
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

    def get_connection(self, client_config):
        connection = FiremonConnection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       username=client_config['username'],
                                       password=client_config['password'],
                                       enrich_ios_version=self.__enrich_ios_version)
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
        The schema FiremonAdapter expects from configs

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
                'verify_ssl',
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_firemon_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.management_ip = device_raw.get('managementIp')
            device_pack = device_raw.get('devicePack')
            if not isinstance(device_pack, dict):
                device_pack = {}
            device.device_type = device_raw.get('deviceType') or device_pack.get('deviceType')
            device.last_updated = parse_date(device_raw.get('lastUpdated'))
            device.last_revision = parse_date(device_raw.get('lastRevision'))
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    @classmethod
    def _parse_ios_control_output(cls, control_raw, device_id):
        if not (isinstance(control_raw, dict) and isinstance(control_raw.get('regexMatches'), list)):
            logger.warning(f'Invalid control_raw received: {control_raw}')
            return None
        regex_matches = control_raw.get('regexMatches')
        result_line = None
        # Grab the appropriate regex match found from target filename
        for match_dict in regex_matches:
            if ((str(match_dict.get('deviceId')) == str(device_id)) and
                    (match_dict.get('filename') == consts.CONTROL_ENRICH_IOS_DEVICE_FILENAME) and
                    (match_dict.get('lineNumber') == 1)):

                result_line = match_dict.get('line')
                break
        return result_line

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.name = device_raw.get('name')
            device.description = device_raw.get('description')
            management_ip = device_raw.get('managementIp')
            if management_ip:
                device.add_ips_and_macs(ips=[management_ip])

            device.last_seen = parse_date(device_raw.get('lastUpdated'))

            ios_control_output = device_raw.get(consts.CONTROL_NAME_ENRICH_IOS)
            if ios_control_output:
                ios_os = self._parse_ios_control_output(ios_control_output, device_id)
                if isinstance(ios_os, str) and ios_os:
                    device.figure_os(ios_os)

            device_pack = device_raw.get('devicePack')
            if not isinstance(device_pack, dict):
                device_pack = {}

            device.device_model = device_raw.get('product') or device_pack.get('deviceName')
            device.device_manufacturer = device_raw.get('vendor') or device_pack.get('vendor')

            self._fill_firemon_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching Firemon Device for {device_raw}')
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
                logger.exception(f'Problem with fetching Firemon Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'enrich_ios_version',
                    'type': 'bool',
                    'default': True,
                    'title': 'Enrich using "Axonius_Enrich_IOS_Version" control'
                },
            ],
            'required': ['enrich_ios_version'],
            'pretty_name': 'Firemon Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'enrich_ios_version': True,
        }

    def _on_config_update(self, config):
        self.__enrich_ios_version = config['enrich_ios_version']
