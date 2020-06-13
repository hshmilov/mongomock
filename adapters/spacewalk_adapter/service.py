import datetime
import xmlrpc.client as xmlrpclib
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from spacewalk_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SpacewalkAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        creation_time = Field(datetime.datetime, 'Creation Time')
        currency_score = Field(int, 'System Currency Score')
        moderate_count = Field(int, 'Moderate Security Errata Count')
        critical_count = Field(int, 'Critical Security Errata Count')
        low_count = Field(int, 'Low Security Errata Count')
        bug_count = Field(int, 'Bug Fix Errata Count')
        important_count = Field(int, 'Important Security Errata Count')
        enhancement_count = Field(int, 'Enhancement Errata Count')
        running_kernel = Field(str, 'Running Kernel')

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
        base_url = RESTConnection.build_url(client_config['domain'], url_base_prefix='/rpc/api')
        connection = xmlrpclib.Server(base_url, verbose=False)
        key = connection.auth.login(client_config['username'], client_config['password'])
        return connection, key

    def _connect_client(self, client_config):
        try:
            self.get_connection(client_config)
            return client_config
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        connection, key = self.get_connection(client_data)
        currency_dict = dict()
        try:
            for currency_raw in connection.system.getSystemCurrencyScores(key):
                currency_dict[currency_raw['sid']] = currency_raw
        except Exception:
            logger.exception(f'Problem getting currency data')
        for device_raw in connection.system.listSystems(key):
            try:
                device_id = device_raw.get('id')
                if not device_id:
                    continue
            except Exception:
                continue
            try:
                if currency_dict.get(device_id):
                    device_raw['currency_raw'] = currency_dict.get(device_id)
            except Exception:
                logger.exception(f'Problemg getting currency for device')
            try:
                device_raw['network'] = connection.system.getNetworkDevices(key, device_id)
            except Exception:
                logger.exception(f'Problem getting network for {device_raw}')
            try:
                device_raw['packages'] = connection.system.listPackages(key, device_id)
            except Exception:
                logger.exception(f'Problem getting packages')
            try:
                device_raw['running_kernel'] = connection.system.getRunningKernel(key, device_id)
            except Exception:
                logger.exception(f'Problem getting running_kernel for {device_raw}')
            yield device_raw

    @staticmethod
    def _clients_schema():
        """
        The schema SpacewalkAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Spacewalk Domain',
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
                }
            ],
            'required': [
                'domain',
                'username',
                'password'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('name')
            device.last_seen = parse_date(device_raw.get('last_checkin'))
            if device_raw.get('last_boot'):
                device.set_boot_time(boot_time=parse_date(str(device_raw.get('last_boot'))))
            device.creation_time = parse_date(device_raw.get('created'))
            try:
                nics = device_raw.get('network') or []
                for nic in nics:
                    ips = []
                    ipv4 = nic.get('ip')
                    if ipv4:
                        ips.extend(ipv4.split(','))
                    name = nic.get('interface')
                    mac = nic.get('hardware_address')
                    try:
                        ipv6s = nic.get('ipv6')
                        for ipv6 in ipv6s:
                            if ipv6.get('address'):
                                ips.append(ipv6.get('address'))
                    except Exception:
                        logger.exception(f'Problem with IPv6')
                    device.add_nic(name=name, mac=mac, ips=ips)
            except Exception:
                logger.exception(f'Problem with nic')
            try:
                packages = device_raw.get('packages')
                if packages is None:
                    packages = []
                for package in packages:
                    try:
                        device.add_installed_software(name=package.get('name'),
                                                      version=package.get('version'))
                    except Exception:
                        logger.exception(f'Problem getting package {package}')
            except Exception:
                logger.exception(f'Problem with packages')
            try:
                currency_raw = device_raw.get('currency_raw')
                if not isinstance(currency_raw, dict):
                    currency_raw = {}
                device.currency_score = currency_raw.get('score') \
                    if isinstance(currency_raw.get('score'), int) else None
                device.moderate_count = currency_raw.get('mod') \
                    if isinstance(currency_raw.get('mod'), int) else None
                device.critical_count = currency_raw.get('crit') \
                    if isinstance(currency_raw.get('crit'), int) else None
                device.low_count = currency_raw.get('low') \
                    if isinstance(currency_raw.get('low'), int) else None
                device.bug_count = currency_raw.get('bug') \
                    if isinstance(currency_raw.get('bug'), int) else None
                device.important_count = currency_raw.get('imp') \
                    if isinstance(currency_raw.get('imp'), int) else None
                device.enhancement_count = currency_raw.get('enh') \
                    if isinstance(currency_raw.get('enh'), int) else None

            except Exception:
                logger.exception(f'Problem parsing ')
            device.running_kernel = device_raw.get('running_kernel')
            for key in device_raw:
                device_raw[key] = str(device_raw[key])
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Spacewalk Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
