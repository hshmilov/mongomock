import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw
from symantec_edr_adapter.connection import SymantecEdrConnection
from symantec_edr_adapter.client_id import get_client_id
from symantec_edr_adapter.structures import SymantecEdrDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecEdrAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(SymantecEdrDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

        # This will be used to map disposition code to value.
        SymantecEdrAdapter.disposition_map = {
            0: 'Good',
            1: 'Unknown',
            2: 'Suspicious',
            3: 'Bad'
        }

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy')
                                                )

    @staticmethod
    def get_connection(client_config):
        connection = SymantecEdrConnection(domain=client_config['domain'],
                                           verify_ssl=client_config['verify_ssl'],
                                           https_proxy=client_config.get('https_proxy'),
                                           proxy_username=client_config.get('proxy_username'),
                                           proxy_password=client_config.get('proxy_password'),
                                           username=client_config.get('username'),
                                           password=client_config('password'))
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
    # pylint: disable=arguments-differ,unnecessary-pass
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        pass

    @staticmethod
    def _clients_schema():
        """
        The schema SymantecEdrAdapter expects from configs

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
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': 'password',
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_symantec_edr_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.ip_address = device_raw.get('device_ip')
            device.agent_version = device_raw.get('agent_version')
            device.domain_or_workgroup = device_raw.get('domain_or_workgroup')
            device.managed_sepm_ip = device_raw.get('managed_sepm_ip')
            device.managed_sepm_version = device_raw.get('managed_sepm_version')

            operating_system = device_raw.get('operating_system')
            disposition_endpoint = device_raw.get('disposition_endpoint')
            sep_group_summary = device_raw.get('sep_group_summary')

            if isinstance(operating_system, dict):
                is_64_arch = parse_bool_from_raw(operating_system.get('is_64_bit'))
                device.os_architecture = '64' if is_64_arch else '32'

            if disposition_endpoint:
                device.disposition_endpoint = SymantecEdrAdapter.disposition_map.get(disposition_endpoint)

            if isinstance(sep_group_summary, dict):
                device.sep_group_name = sep_group_summary.get('name')
                domain_summary = sep_group_summary.get('sep_domain_summary')
                if isinstance(domain_summary, dict):
                    device.sep_domain_name = domain_summary.get('name')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('device_uid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            device.id = device_id
            device.name = device_raw.get('device_name')
            device.pc_type = device_raw.get('type')
            device.current_logged_user = device_raw.get('user_name')
            device.first_seen = parse_date(device_raw.get('firstSeen'))
            device.last_seen = parse_date(device_raw.get('lastSeen'))
            operating_system = device_raw.get('operating_system')

            if isinstance(operating_system, dict):
                device.os = operating_system.get('osfullname')
            device.add_ips_and_macs(
                ips=device_raw.get('ip_addresses'),
                macs=device_raw.get('mac_addresses')
            )

            if not device.first_seen or not device.last_seen:
                logger.exception(f'Could not parse first and last seen dates for {device_raw}')

            self._fill_symantec_edr_device_fields(device_raw, device)
            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching SymantecEdr Device for {device_raw}')
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
                logger.exception(f'Problem with fetching SymantecEdr Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
