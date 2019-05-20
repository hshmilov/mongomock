import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from cloudpassage_adapter.connection import CloudpassageConnection
from cloudpassage_adapter.client_id import get_client_id
from cloudpassage_adapter.consts import DEFAULT_DOMAIN_NAME

logger = logging.getLogger(f'axonius.{__name__}')


class CloudpassageAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        server_label = Field(str, 'Server Label')
        reported_fqdn = Field(str, 'Reported FQDN')
        server_state = Field(str, 'Server State')
        daemon_version = Field(str, 'Daemon Version')
        read_only = Field(bool, 'Read Only')
        proxy = Field(str, 'Proxy')
        primary_ip_address = Field(str, 'Primary IP Address')
        connecting_ip_address = Field(str, 'Connecting IP Address')

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
        connection = CloudpassageConnection(domain=client_config.get('domain') or DEFAULT_DOMAIN_NAME,
                                            verify_ssl=client_config['verify_ssl'],
                                            https_proxy=client_config.get('https_proxy'),
                                            username=client_config['key_id'],
                                            password=client_config['key_secret'])
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
        The schema CloudpassageAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cloudpassage Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN_NAME
                },
                {
                    'name': 'key_id',
                    'title': 'Key ID',
                    'type': 'string'
                },
                {
                    'name': 'key_secret',
                    'title': 'Key Secret',
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
                'key_id',
                'key_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912,R0915
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('hostname') or '')
            device.hostname = device_raw.get('hostname')
            device.server_label = device_raw.get('server_label')
            device.reported_fqdn = device_raw.get('reported_fqdn')
            device.server_state = device_raw.get('state')
            device.daemon_version = device_raw.get('daemon_version')
            device.proxy = device_raw.get('proxy')
            device.group_name = device_raw.get('group_name')
            try:
                primary_ip_address = device_raw.get('primary_ip_address')
                if primary_ip_address:
                    device.primary_ip_address = primary_ip_address
                    device.add_nic(None, [primary_ip_address])
                connecting_ip_address = device_raw.get('connecting_ip_address')
                if connecting_ip_address:
                    device.connecting_ip_address = connecting_ip_address
                    device.add_nic(None, [connecting_ip_address])
                interfaces = device_raw.get('interfaces')
                if interfaces and isinstance(interfaces, list):
                    for nic in interfaces:
                        try:
                            ips = [nic.get('ip_address')] if nic.get('ip_address') else None
                            mac = nic.get('mac_address') if nic.get('mac_address') else None
                            nic_name = nic.get('name')
                            device.add_nic(name=nic_name, ips=ips, mac=mac)
                        except Exception:
                            logger.exception(f'Problem adding nic {nic}')
            except Exception:
                logger.exception(f'Problem adding nics to {device_raw}')
            try:
                device.read_only = device_raw.get('read_only')
            except Exception:
                logger.exception(f'Problem wiht read only for {device_raw}')
            try:
                if device_raw.get('csp_provider') == 'azure':
                    device.cloud_provider = 'Azure'
                elif device_raw.get('csp_provider') == 'gcp':
                    device.cloud_provider = 'GCP'
                elif device_raw.get('csp_provider') == 'aws_ec2':
                    device.cloud_provider = 'AWS'
                device.cloud_id = device_raw.get('csp_account_id')

            except Exception:
                logger.exception(f'Problem getting cloud stuff for {device_raw}')
            try:
                device.figure_os((device_raw.get('platform') or '') + ' ' + (device_raw.get('platform_version') or ''))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            try:
                device.last_state_change = parse_date(device_raw.get('last_state_change'))
            except Exception:
                logger.exception(f'Problem with last state change')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Cloudpassage Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
