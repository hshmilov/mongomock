import ipaddress
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.awake.connection import AwakeConnection
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.mixins.configurable import Configurable
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from awake_adapter.client_id import get_client_id
from awake_adapter.structures import AwakeDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class AwakeAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(AwakeDeviceInstance):
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
        connection = AwakeConnection(domain=client_config.get('domain'),
                                     verify_ssl=client_config.get('verify_ssl'),
                                     https_proxy=client_config.get('https_proxy'),
                                     proxy_username=client_config.get('proxy_username'),
                                     proxy_password=client_config.get('proxy_password'),
                                     username=client_config.get('username'),
                                     password=client_config.get('password'))
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
        The schema AwakeAdapter expects from configs

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
    def _fill_awake_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.white_listed = parse_bool_from_raw(device_raw.get('whiteListed'))
            device.ack_time = parse_date(device_raw.get('ackTime'))
            device.number_sessions = int_or_none(device_raw.get('numberSessions'))
            device.number_similar_devices = int_or_none(device_raw.get('numberSimilarDevices'))
            device.notability_percentile = int_or_none(device_raw.get('notabilityPercentile'))
            device.device_type = device_raw.get('deviceType')
            device.duration = device_raw.get('duration')
            if isinstance(device_raw.get('application'), list) and device_raw.get('application'):
                device.application = device_raw.get('application')
            try:
                if isinstance(device_raw.get('monitoringPointIds'), list) and device_raw.get('monitoringPointIds'):
                    device.monitoring_point_ids = device_raw.get('monitoringPointIds')
            except Exception:
                pass
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    # pylint: disable=too-many-locals, too-many-nested-blocks, too-many-branches, too-many-statements
    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('deviceId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('deviceName') or '')
            hostname = device_raw.get('deviceName')
            if ':' in hostname:
                device.hostname = hostname.split(':')[-1]
                device.last_used_users = [hostname.split(':')[0]]
            else:
                device.hostname = hostname
            device.first_seen = parse_date(device_raw.get('firstSeen'))
            device.last_seen = parse_date(device_raw.get('lastSeen'))
            device.figure_os(device_raw.get('os'))
            if isinstance(device_raw.get('ips'), list):
                ips = device_raw.get('ips')
                try:
                    if self.__cidr_blacklist_networks:
                        for ip in ips:
                            ip = ipaddress.IPv4Address(ip)
                            if any(ip in bnc for bnc in self.__cidr_blacklist_networks):
                                # this address is in the cidr blacklist
                                return None
                except Exception:
                    logger.exception(f'Problem with ip black list')
                device.add_nic(ips=device_raw.get('ips'))
            self._fill_awake_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Awake Device for {device_raw}')
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
                logger.exception(f'Problem with fetching Awake Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'cidr_blacklist',
                    'title': 'CIDR Blacklist',
                    'type': 'string'
                }
            ],
            'required': [
            ],
            'pretty_name': 'Awake Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'cidr_blacklist': None
        }

    def _on_config_update(self, config):
        cidr_blacklist = config.get('cidr_blacklist')
        self.__cidr_blacklist_networks = []
        if cidr_blacklist and isinstance(cidr_blacklist, str):
            for cidr_blacklist_network in cidr_blacklist.split(','):
                try:
                    self.__cidr_blacklist_networks.append(ipaddress.IPv4Network(cidr_blacklist_network.strip()))
                except Exception:
                    logger.exception(f'Could not add cidr {cidr_blacklist_network} to blacklist')
