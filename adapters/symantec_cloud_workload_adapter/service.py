import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.fields import Field, ListField
from axonius.clients.rest.connection import RESTException
from axonius.utils.parsing import figure_out_cloud
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import is_domain_valid
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from symantec_cloud_workload_adapter.connection import SymantecCloudWorkloadConnection
from symantec_cloud_workload_adapter.client_id import get_client_id
from symantec_cloud_workload_adapter.consts import DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecCloudWorkloadAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        instance_state = Field(str, 'Instance State')
        instance_type = Field(str, 'Instance Type')
        subscription_id = Field(str, 'Subscription Id')
        subscription_name = Field(str, 'Subscription Name')
        resource_group_name = Field(str, 'Resource Group Name')
        vm_type = Field(str, 'VM Type')
        machine_image_id = Field(str, 'Machine Image Id')
        region = Field(str, 'Region')
        agent_installed = Field(str, 'Agnet Installed')
        subnet_id = Field(str, 'Subnet Id')
        public_dns = Field(str, 'Public DNS')
        updated = Field(bool, 'Updated')
        deleted = Field(bool, 'Deleted')
        created = Field(datetime.datetime, 'Creation Time')
        modified = Field(datetime.datetime, 'Modification Time')
        reconciled = Field(bool, 'Reconciled')
        firewall_groups = ListField(str, 'Firewall Groups')
        obj_classes = ListField(str, 'Object Classes')
        policy_applied = Field(str, 'Policy Applied')
        availability_zone = Field(str, 'Availability Zone')
        agent_id = Field(str, 'Agent Id')
        agent_version = Field(str, 'Agent Version')

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
        connection = SymantecCloudWorkloadConnection(domain=client_config.get('domain') or DEFAULT_DOMAIN,
                                                     verify_ssl=client_config['verify_ssl'],
                                                     https_proxy=client_config.get('https_proxy'),
                                                     domain_id=client_config['domain_id'],
                                                     customer_id=client_config['customer_id'],
                                                     client_id=client_config['client_id'],
                                                     client_secret=client_config['client_secret'])
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
        The schema SymantecCloudWorkloadAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'SymantecCloudWorkload Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN
                },
                {
                    'name': 'domain_id',
                    'title': 'Domain Id',
                    'type': 'string'
                },
                {
                    'name': 'customer_id',
                    'title': 'Customer Id',
                    'type': 'string'
                },
                {
                    'name': 'client_id',
                    'title': 'Client Id',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
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
                }
            ],
            'required': [
                'domain',
                'domain_id',
                'customer_id',
                'client_id',
                'client_secret',
                'verify_ssl'
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
            device.id = device_id + '_' + (device_raw.get('host') or '')
            device.hostname = device_raw.get('fqdn')
            device.name = device_raw.get('host')
            mac = device_raw.get('mac_address')
            if not mac or not isinstance(mac, str):
                mac = None
            ips = device_raw.get('ip_addresses')
            private_ips = device_raw.get('private_ips')
            if not private_ips or not isinstance(private_ips, list):
                private_ips = None
            if not ips or not isinstance(ips, list):
                ips = private_ips
            if private_ips:
                for ip in private_ips:
                    if ip not in ips:
                        ips.append(ip)
            if mac or ips:
                device.add_nic(mac, ips)
            device.cloud_id = device_raw.get('instance_id')
            try:
                device.cloud_provider = figure_out_cloud((device_raw.get('cloud_platform') or {}).get('value'))
            except Exception:
                logger.exception(f'Problem getting cloud platform for {device_raw}')
            try:
                device.instance_state = (device_raw.get('instance_state') or {}).get('display_value')
            except Exception:
                logger.exception(f'Problem getting instance stats for {device_raw}')
            device.instance_type = device_raw.get('instance_type')
            device.subscription_id = device_raw.get('subscription_id')
            device.subscription_name = device_raw.get('subscription_name')
            device.policy_applied = device_raw.get('policy_applied')
            device.resource_group_name = device_raw.get('resource_group_name')
            device.vm_type = device_raw.get('vm_type')
            device.machine_image_id = device_raw.get('machine_image_id')
            device.region = device_raw.get('region')
            device.availability_zone = device_raw.get('availability_zone')
            domain = device_raw.get('domain')
            try:
                security_agent = device_raw.get('security_agent')
                if isinstance(security_agent, dict):
                    device.agent_id = security_agent.get('agent_id')
                    device.agent_version = security_agent.get('agent_version')
                    device.last_seen = parse_date(security_agent.get('last_connected_time'))
            except Exception:
                logger.exception(f'Problem getting agent data for {device_raw}')
            try:
                hw = device_raw.get('hw')
                if isinstance(hw, dict):
                    device.add_cpu(cores=hw.get('phys_cpus'))
            except Exception:
                logger.exception(f'Problem getting hw for {device_raw}')
            if is_domain_valid(domain):
                device.domain = domain
            try:
                device.agent_installed = (device_raw.get('agent_installed') or {}).get('display_value')
            except Exception:
                logger.exception(f'Problem getting agent status for {device_raw}')
            device.figure_os(device_raw.get('platform'))
            device.subnet_id = device_raw.get('subnet_id')
            device.public_dns = device_raw.get('public_dns')
            device.updated = bool(device_raw.get('updated'))
            device.deleted = bool(device_raw.get('deleted'))
            device.created = parse_date(device_raw.get('created'))
            device.modified = parse_date(device_raw.get('modified'))
            device.reconciled = bool(device_raw.get('reconciled'))
            try:
                if isinstance(device_raw.get('obj_classes'), list):
                    device.obj_classes = device_raw.get('obj_classes')
            except Exception:
                logger.exception(f'Problem getting obj classes for {device_raw}')
            try:
                if isinstance(device_raw.get('firewall_groups'), list):
                    device.firewall_groups = device_raw.get('firewall_groups')
            except Exception:
                logger.exception(f'Problem getting firewall_groups  for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching SymantecCloudWorkload Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Assets]
