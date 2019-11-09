import json
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.dynamic_fields import put_dynamic_field
from axonius.utils.files import get_local_config_file
from google_big_query_adapter.connection import GoogleBigQueryConnection
from google_big_query_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class GoogleBigQueryAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability('https://bigquery.googleapis.com/discovery/v1/apis/bigquery/v2/rest')

    def get_connection(self, client_config):
        connection = GoogleBigQueryConnection(
            domain='https://bigquery.googleapis.com',
            https_proxy=client_config.get('https_proxy'),
            service_account_file=json.loads(self._grab_file_contents(client_config['keypair_file'])),
            project_id=client_config['project_id'],
            dataset_id=client_config['dataset_id']
        )
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = f'Error connecting to client {self._get_client_id(client_config)} - {str(e)}'
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
        The schema GoogleBigQueryAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'project_id',
                    'title': 'Project ID',
                    'description': 'The ID of the Google Cloud Project',
                    'type': 'string'
                },
                {
                    'name': 'dataset_id',
                    'title': 'Dataset ID',
                    'description': 'The ID of the Google Big Query Dataset',
                    'type': 'string'
                },
                {
                    'name': 'keypair_file',
                    'title': 'JSON Key pair for the service account authentication',
                    'description': 'The binary contents of the JSON keypair file',
                    'type': 'file',
                }
            ],
            'required': [
                'project_id',
                'dataset_id',
                'keypair_file'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    def _create_device(self, device_raw):
        try:
            device_raw = dict(device_raw)
            device = self._new_device_adapter()
            device_id = device_raw.get('instance_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.cloud_id = device_id
            device.cloud_provider = 'AWS'

            try:
                if device_raw.get('private_ip_address'):
                    device.add_nic(ips=[device_raw.get('private_ip_address')])
            except Exception:
                logger.exception(f'Failed getting private ip address')

            try:
                public_ip_address = device_raw.get('public_ip_address')
                if public_ip_address:
                    device.add_nic(ips=[public_ip_address])
                    device.add_public_ip(device_raw.get('public_ip_address'))
            except Exception:
                logger.exception(f'Failed getting private ip address')

            try:
                network_interfaces = device_raw.get('network_interfaces')
                if network_interfaces and isinstance(network_interfaces, list):
                    for network_interface_item in network_interfaces:
                        ips = network_interface_item.get('private_ip_address')
                        ips = [ips] if ips else None

                        mac = network_interface_item.get('mac_address')
                        mac = mac if mac else None
                        if mac or ips:
                            device.add_nic(mac=mac, ips=ips)
            except Exception:
                logger.exception(f'Failed adding network interface')

            try:
                tags = device_raw.get('tags')
                if tags and isinstance(tags, list):
                    for tag_item in tags:
                        if tag_item.get('key') and str(tag_item.get('key')).lower() == 'name':
                            device.name = tag_item.get('value')
            except Exception:
                logger.exception(f'Failed getting tags')

            for key, value in device_raw.items():
                try:
                    put_dynamic_field(device, f'ec2_instances_{key}', value, f'ec2_instances.{key}')
                except Exception:
                    logger.exception(f'Failed putting key {key} with value {value}')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Google Big Query Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
