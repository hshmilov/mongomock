import logging

from axonius.fields import Field
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from cloud_health_adapter.consts import DEFAULT_CLOUD_HEALTH_DOMAIN, AWS_INSTANCE
from cloud_health_adapter.client_id import get_client_id
from cloud_health_adapter.connection import CloudHealthConnection
from cloud_health_adapter.structures import AwsInstance

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class CloudHealthAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        device_source = Field(str, 'Device Source')
        aws_instance = Field(AwsInstance, 'AWS Instance')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config['domain'])

    @staticmethod
    def get_connection(client_config):
        connection = CloudHealthConnection(api_key=client_config['api_key'],
                                           domain=client_config['domain'],
                                           https_proxy=client_config.get('https_proxy'))

        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as err:
            message = f'Error connecting to client, reason: {str(err)}'
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
        The schema CloudHealthAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CloudHealth Domain',
                    'type': 'string',
                    'default': DEFAULT_CLOUD_HEALTH_DOMAIN
                },
                {
                    'name': 'api_key',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'api_key'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    @staticmethod
    def _fill_aws_fields(device_raw):
        try:
            aws_instance = AwsInstance()
            aws_instance.state = device_raw.get('state')
            aws_instance.attached_ebs = device_raw.get('attached_ebs')
            aws_instance.launch_date = parse_date(device_raw.get('launch_date'))
            aws_instance.price_per_month = device_raw.get('price_per_month')
            aws_instance.total_cost_per_month = device_raw.get('total_cost_per_month')
            aws_instance.current_projected_cost = device_raw.get('current_projected_cost')
            aws_instance.hourly_cost = device_raw.get('hourly_cost')
            aws_instance.key = device_raw.get('key')
            aws_instance.is_monitored = device_raw.get('is_monitored')
            aws_instance.is_spot = device_raw.get('is_spot')
            aws_instance.is_ebs_optimized = device_raw.get('is_ebs_optimized')
            aws_instance.root_device_name = device_raw.get('root_device_name')
            aws_instance.root_device_type = device_raw.get('root_device_type')
            aws_instance.owner_email = device_raw.get('root_device_type')
            aws_instance.virtualization_type = device_raw.get('virtualization_type')
            aws_instance.hypervisor = device_raw.get('hypervisor')

            public_dns = device_raw.get('dns')
            if not public_dns:
                public_dns = []
            if isinstance(public_dns, str):
                public_dns = [public_dns]
            if public_dns:
                for dns in public_dns:
                    if dns:
                        aws_instance.public_dns.append(dns)

            private_ip = device_raw.get('private_ip')
            if not private_ip:
                private_ip = []
            if isinstance(private_ip, str):
                private_ip = [private_ip]
            if private_ip:
                for ip in private_ip:
                    if ip:
                        aws_instance.private_ip.append(ip)

            private_dns = device_raw.get('private_dns')
            if not private_dns:
                private_dns = []
            if isinstance(private_dns, str):
                private_dns = [private_dns]
            if private_dns:
                for dns in private_dns:
                    if dns:
                        aws_instance.private_dns.append(dns)

            return aws_instance
        except Exception:
            logger.exception(f'failed to parse aws instance info for device {device_raw}')
            return None

    def _fill_device_fields(self, device, device_raw, device_source):
        try:
            device_id = device_raw.get('instance_id')
            if not device_id:
                message = f'Bad device with no ID {device_raw}'
                logger.warning(message)
                raise Exception(message)
            device.id = str(device_id) + '_' + device_raw.get('name')
            device.name = device_raw.get('name')
            device.hostname = device_raw.get('private_dns')

            ips = device_raw.get('private_ip') or []
            if isinstance(ips, str):
                ips = [ips]

            public_ips = device_raw.get('ip')
            if not public_ips:
                public_ips = []
            if isinstance(public_ips, str):
                public_ips = [public_ips]
            if public_ips:
                for ip in public_ips:
                    if ip:
                        ips.append(ip)
                        device.add_public_ip(ip)

            device.add_ips_and_macs(ips=ips)

            try:
                os_string = (device_raw.get('architecture') or '') + ' ' + \
                            (device_raw.get('image_id') or '')
                device.figure_os(os_string)
            except Exception:
                logger.exception(f'Failed to parse OS for device {device_raw}')

            try:
                device.device_source = device_source
                if device_source == AWS_INSTANCE:
                    device.aws_instance = self._fill_aws_fields(device_raw)
            except Exception:
                logger.exception(f'Failed to fill fields for {device_raw}')

        except Exception:
            logger.exception(f'Failed to parse device {device_raw}')
            raise

    def _create_device(self, device_raw, device_source):
        try:
            device = self._new_device_adapter()
            self._fill_device_fields(device, device_raw, device_source)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CloudHealth Device for {device_raw} for source {device_source}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_source in devices_raw_data:
            if not device_raw:
                continue
            try:
                device = self._create_device(device_raw, device_source)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
