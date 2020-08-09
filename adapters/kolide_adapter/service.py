import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import is_valid_ip, format_mac
from kolide_adapter.client_id import get_client_id
from kolide_adapter.connection import KolideConnection
from kolide_adapter.structures import KolideDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class KolideAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(KolideDeviceInstance):
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
        connection = KolideConnection(domain=client_config.get('domain'),
                                      verify_ssl=client_config.get('verify_ssl'),
                                      https_proxy=client_config.get('https_proxy'),
                                      proxy_username=client_config.get('proxy_username'),
                                      proxy_password=client_config.get('proxy_password'),
                                      apikey=client_config.get('apikey'))
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
    def _clients_schema():
        """
        The schema KolideAdapter expects from configs

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
                    'name': 'apikey',
                    'title': 'API Token',
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
                'verify_ssl',
                'apikey'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_kolide_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.osquery_version = device_raw.get('osquery_version')
            device.status = device_raw.get('status')
            device.updated_at = parse_date(device_raw.get('updated_at'))
            device.detail_update_time = parse_date(device_raw.get('detail_updated_at'))
            device.created_at = parse_date(device_raw.get('created_at'))
            device.platform = device_raw.get('platform')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('hostname', ''))

            device.hostname = device_raw.get('hostname')
            seen_time = parse_date(device_raw.get('seen_time'))
            updated_at = parse_date(device_raw.get('updated_at'))
            if seen_time and updated_at:
                device.last_seen = max(seen_time, updated_at)
            else:
                device.last_seen = seen_time or updated_at

            if device_raw.get('cpu_type') in ['amd64', '64-bit', 'x64', '64 bit', 'x86_64', 'Win64']:
                architecture = 'x64'
            elif device_raw.get('cpu_type') in ['32-bit', 'x86']:
                architecture = 'x86'
            else:
                architecture = device_raw.get('cpu_type')

            try:
                device.add_cpu(manufacturer=device_raw.get('cpu_brand'), cores=device_raw.get('cpu_logical_cores'),
                               architecture=architecture)
            except Exception as e:
                logger.warning(
                    f'Couldn\'t add cpu: manufacturer: {device_raw.get("cpu_brand")},'
                    f' cores: {device_raw.get("cpu_logical_cores")}, architecture: {architecture}, Error: {str(e)}')

            try:
                device.add_connected_hardware(name=device_raw.get('hardware_model'),
                                              manufacturer=device_raw.get('hardware_vendor'),
                                              hw_id=device_raw.get('hardware_serial'))
            except Exception as e:
                logger.warning(
                    f'Couldn\'t add hardware: name: {device_raw.get("hardware_model")},'
                    f' manufacturer: {device_raw.get("hardware_vendor")}, '
                    f'hw_id: {device_raw.get("hardware_serial")}, Error: {str(e)}')

            device.figure_os(device_raw.get('os_version'))

            ip = device_raw.get('primary_ip') if is_valid_ip(device_raw.get('primary_ip')) else None
            try:
                device.add_nic(mac=format_mac(device_raw.get('primary_mac')), ips=[ip])
            except Exception as e:
                logger.warning(
                    f'Couldn\'t add nic: mac: {device_raw.get("primary_mac")},'
                    f' ip: {device_raw.get("primary_ip")}, Error: {str(e)}')
            device.add_public_ip(ip)

            device.uuid = device_raw.get('uuid')
            device.first_seen = parse_date(device_raw.get('created_at'))

            self._fill_kolide_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching Kolide Device for {device_raw}')
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
                logger.exception(f'Problem with fetching Kolide Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
