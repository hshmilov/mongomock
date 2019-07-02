import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.parsing import parse_unix_timestamp
from axonius.utils.files import get_local_config_file
from alertlogic_adapter.connection import AlertlogicConnection
from alertlogic_adapter.client_id import get_client_id
from alertlogic_adapter.consts import DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class AlertlogicAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        created_at = Field(datetime.datetime, 'Creation Time')
        created_by = Field(str, 'Created By')
        modified_at = Field(datetime.datetime, 'Modification Time')
        modified_by = Field(str, 'Modified By')
        bucket = Field(str, 'Bucket')
        service_offering = Field(str, 'Service Offering')
        agent_version = Field(str, 'Agent Version')
        network_id = Field(str, 'Network Id')
        update_policy_id = Field(str, 'Update Policy Id')
        customer_id = Field(str, 'Customer Id')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain') or DEFAULT_DOMAIN)

    @staticmethod
    def get_connection(client_config):
        connection = AlertlogicConnection(domain=client_config.get('domain') or DEFAULT_DOMAIN,
                                          verify_ssl=client_config['verify_ssl'],
                                          https_proxy=client_config.get('https_proxy'),
                                          username=client_config['apikey'])
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
        The schema AlertlogicAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Alert Logic Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN
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
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            if device_raw.get('type') != 'host':
                return None
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.name = device_raw.get('name')
            metadata = device_raw.get('metadata')
            try:
                if isinstance(metadata, dict):
                    device.bucket = metadata.get('bucket')
                    device.cloud_id = metadata.get('cloud_id')
                    if str(metadata.get('cloud_id')).startswith('i-'):
                        device.cloud_provider = 'AWS'
                    device.hostname = metadata.get('local_hostname')
                    ips = []
                    if metadata.get('local_ipv4') and isinstance(metadata.get('local_ipv4'), list):
                        ips += metadata.get('local_ipv4')
                    if metadata.get('local_ipv6') and isinstance(metadata.get('local_ipv6'), list):
                        ips += metadata.get('local_ipv6')
                    if ips:
                        device.add_nic(ips=ips)
                    device.figure_os((metadata.get('os_type') or '') + ' ' + (metadata.get('os_details') or ''))
                    if isinstance(metadata.get('num_logical_processors'), int):
                        device.total_number_of_cores = metadata.get('num_logical_processors')
                    device.service_offering = metadata.get('service_offering')
                    if isinstance(metadata.get('total_mem_mb'), int):
                        device.total_physical_memory = metadata.get('total_mem_mb') / 1024.0
                    device.agent_version = metadata.get('version')

            except Exception:
                logger.exception(f'Problem with Metadata at {device_raw}')
            device.network_id = device_raw.get('network_id')
            try:
                device.device_status = device_raw.get('status').get('status')
            except Exception:
                logger.exception(f'Problem getting status for {device_raw}')
            created = device_raw.get('created')
            if created and isinstance(created, dict):
                device.created_by = created.get('by')
                device.created_at = parse_unix_timestamp(created.get('at'))
            modified = device_raw.get('modified')
            if modified and isinstance(modified, dict):
                device.modified_by = modified.get('by')
                device.modified_at = parse_unix_timestamp(modified.get('at'))
            try:
                device.update_policy_id = (device_raw.get('update_policy') or {}).get('id')
            except Exception:
                logger.exception(f'Problem getting update policy for {device_raw}')
            try:
                device.customer_id = (device_raw.get('customer') or {}).get('id')
            except Exception:
                logger.exception(f'Problem getting customer for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Alertlogic Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
