import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import is_domain_valid
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from webroot_adapter.connection import WebrootConnection
from webroot_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class WebrootAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        policy_name = Field(str, 'Policy Name')
        group_name = Field(str, 'Group Name')
        last_infected = Field(datetime.datetime, 'Last Infected')

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
        connection = WebrootConnection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       gsm_key=client_config['gsm_key'],
                                       site_id=client_config['site_id'],
                                       apikey=client_config['apikey'])
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
        The schema WebrootAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Webroot Domain',
                    'type': 'string'
                },
                {
                    'name': 'gsm_key',
                    'title': 'GSM Key',
                    'type': 'string'
                },
                {
                    'name': 'site_id',
                    'title': 'Site ID',
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
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'gsm_key',
                'site_id',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('EndpointId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('HostName') or '')
            device.hostname = device_raw.get('HostName')
            device.agent_version = device_raw.get('AgentVersion')
            try:
                device.last_seen = parse_date(device_raw.get('LastSeen'))
            except Exception:
                logger.exception(f'Problem gettins last seen for {device_raw}')
            try:
                device.first_seen = parse_date(device_raw.get('FirstSeen'))
            except Exception:
                logger.exception(f'Problem gettins first seen for {device_raw}')
            device.add_public_ip(device_raw.get('LastPublicIP'))
            try:
                device.figure_os(device_raw.get('WindowsFullOS'))
            except Exception:
                logger.exception(f'Problem gettins os for {device_raw}')
            device.group_name = device_raw.get('GroupName')
            domain = device_raw.get('ADDomain')
            if is_domain_valid(domain):
                device.domain = domain
            try:
                mac = device_raw.get('MACAddress')
                if not mac:
                    mac = None
                ips = device_raw.get('InternalIP')
                if not ips:
                    ips = None
                else:
                    ips = ips.split(',')
                if mac or ips:
                    device.add_nic(mac, ips)
            except Exception:
                logger.exception(f'Problem adding nic to {device_raw}')
            try:
                if device_raw.get('CurrentUser'):
                    device.last_used_users = device_raw.get('CurrentUser').split(',')
            except Exception:
                logger.exception(f'Problem adding user for {device_raw}')
            try:
                device.last_infected = parse_date(device_raw.get('LastInfected'))
            except Exception:
                logger.exception(f'Problem getting last infected for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Webroot Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
