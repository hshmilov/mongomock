import logging
from urllib.parse import urlparse

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none
from prisma_cloud_adapter.connection import PrismaCloudConnection
from prisma_cloud_adapter.client_id import get_client_id
from prisma_cloud_adapter.structures import PrismaCloudInstance
from prisma_cloud_adapter.consts import URL_API_FORMAT, CloudInstances, DEFAULT_HOURS_FILTER
from prisma_cloud_adapter.structures import EC2Instance, AzureInstance, GCPInstance, SecurityGroup, SecurityRule, \
    SharedFields

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class PrismaCloudAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(PrismaCloudInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _create_api_url(client_config):
        parsed_url = urlparse(client_config['domain'])
        scheme = parsed_url.scheme or 'https'
        domain = parsed_url.netloc or parsed_url.path
        api_domain = domain.replace('app', 'api', 1)

        api_url = URL_API_FORMAT.format(scheme, api_domain)
        return api_url

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        api_url = PrismaCloudAdapter._create_api_url(client_config)
        return RESTConnection.test_reachability(api_url, https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        api_url = PrismaCloudAdapter._create_api_url(client_config)

        connection = PrismaCloudConnection(domain=api_url,
                                           verify_ssl=client_config['verify_ssl'],
                                           https_proxy=client_config.get('https_proxy'),
                                           username=client_config['username'],
                                           password=client_config['password'])
        with connection:
            pass  # check the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint: disable=arguments-differ
    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        hours_filter = DEFAULT_HOURS_FILTER
        if self._last_seen_timedelta:
            # Convert seconds to hours -> seconds / seconds in 1 hour
            hours_filter = int_or_none(self._last_seen_timedelta.seconds / 3600) or DEFAULT_HOURS_FILTER

        with client_data:
            yield from client_data.get_device_list(
                hours_filter=hours_filter
            )

    @staticmethod
    def _clients_schema():
        """
        The schema PrismaCloudAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Prisma Cloud Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'Access key ID',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Secret key',
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    @staticmethod
    def _fill_ec2_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            ec2_instance = EC2Instance()

            ec2_instance.vpc_id = device_raw.get('vpcId')
            ec2_instance.image_id = device_raw.get('imageId')
            ec2_instance.subnet_id = device_raw.get('subnetId')
            ec2_instance.hypervisor = device_raw.get('hypervisor')
            ec2_instance.instance_id = device_raw.get('instanceId')
            ec2_instance.launch_time = parse_date(device_raw.get('launchTime'))
            ec2_instance.client_token = device_raw.get('client_token')
            ec2_instance.optimized_ebs = device_raw.get('ebsOptimized')
            ec2_instance.instance_type = device_raw.get('instanceType')
            ec2_instance.root_device_name = device_raw.get('rootDeviceName')
            ec2_instance.root_device_type = device_raw.get('rootDeviceType')

            if device_raw.get('cpuOptions') and isinstance(device_raw.get('cpuOptions'), dict):
                ec2_instance.core_count = device_raw.get('cpuOptions').get('coreCount')
                ec2_instance.threads_per_core = device_raw.get('cpuOptions').get('threadsPerCore')

            group_ids = []
            group_names = []
            if device_raw.get('securityGroups') and isinstance(device_raw.get('securityGroups'), list):
                for security_group in device_raw.get('securityGroups'):
                    if security_group.get('groupId'):
                        group_ids.append(security_group.get('groupId'))
                    if security_group.get('groupName'):
                        group_names.append(security_group.get('groupName'))
                if group_ids:
                    ec2_instance.security_group_ids = group_ids
                if group_names:
                    ec2_instance.security_group_names = group_names

            os_string = device_raw.get('architecture') or ''
            device.figure_os(os_string=os_string)

            private_dns_names = []
            if device_raw.get('networkInterfaces') and isinstance(device_raw.get('networkInterfaces'), list):
                for network_interface in device_raw.get('networkInterfaces'):
                    if network_interface.get('privateDnsName'):
                        private_dns_names.append(network_interface.get('privateDnsName'))

                    ips = []
                    if network_interface.get('privateIpAddress'):
                        ips = [network_interface.get('privateIpAddress')]
                    device.add_nic(mac=network_interface.get('macAddress'),
                                   ips=ips)
                if private_dns_names:
                    device.dns_servers = private_dns_names

            device.ec2_instance = ec2_instance
        except Exception:
            logger.exception(f'Failed creating ec2 instance for device {device_raw}')

    @staticmethod
    def _fill_azure_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            azure_instance = AzureInstance()

            azure_instance.vm_id = device_raw.get('vmId')
            device.cloud_id = device_raw.get('vmId')
            azure_instance.location = device_raw.get('location')
            azure_instance.power_state = device_raw.get('powerState')

            if device_raw.get('properties.osProfile') and isinstance(device_raw.get('properties.osProfile'), dict):
                azure_instance.computer_name = device_raw.get('properties.osProfile').get('computerName')
                azure_instance.admin_user_name = device_raw.get('properties.osProfile').get('adminUserName')

            if device_raw.get('properties.storageProfile') and isinstance(device_raw.get('properties.storageProfile'),
                                                                          dict):
                storage_profile = device_raw.get('properties.storageProfile')
                if storage_profile.get('imageReference') and isinstance(storage_profile.get('imageReference'), dict):
                    azure_instance.sku = storage_profile.get('imageReference').get('sku')

                if storage_profile.get('osDisk') and isinstance(storage_profile.get('osDisk'), dict):
                    os_name = storage_profile.get('osDisk').get('name')
                    os_type = storage_profile.get('osDisk').get('osType')
                    os_string = (os_name or '') + ' ' + (os_type or '')
                    device.figure_os(os_string=os_string)

            if device_raw.get('properties.networkProfile') and isinstance(device_raw.get('properties.networkProfile'),
                                                                          dict):
                network_profiles = device_raw.get('properties.networkProfile')
                if network_profiles.get('networkInterfaces') and isinstance(network_profiles.get('networkInterfaces'),
                                                                            list):
                    public_ips = []
                    for network_profile in network_profiles.get('networkInterfaces'):
                        public_ips.append(network_profile.get('publicIpAddress'))
                    device.add_ips_and_macs(ips=public_ips)

            device.azure_instance = azure_instance
        except Exception:
            logger.exception(f'Failed creating azure instance for device {device_raw}')

    @staticmethod
    def _fill_gcp_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            gcp_instance = GCPInstance()

            gcp_instance.id = device_raw.get('id')
            gcp_instance.kind = device_raw.get('kind')
            gcp_instance.name = device_raw.get('name')
            gcp_instance.status = device_raw.get('status')
            gcp_instance.cpu_platform = device_raw.get('cpuPlatform')
            gcp_instance.description = device_raw.get('description')
            gcp_instance.creation_time = parse_date(device_raw.get('creationTimestamp'))

            if device_raw.get('labels') and isinstance(device_raw.get('labels'), dict):
                gcp_instance.vm_type = device_raw.get('labels').get('vm-type')

            if device_raw.get('networkInterfaces') and isinstance(device_raw.get('networkInterfaces'), list):
                public_ips = []
                for network_profile in device_raw.get('networkInterfaces'):
                    if network_profile.get('networkIP'):
                        public_ips.append(network_profile.get('networkIP'))
                device.add_ips_and_macs(ips=public_ips)

            device.gcp_instance = gcp_instance
        except Exception:
            logger.exception(f'Failed creating gcp instance for device {device_raw}')

    @staticmethod
    def _parse_security_rules(security_rules: list):
        rules = []
        for security_rule in security_rules:
            try:
                rule = SecurityRule()
                rule.name = security_rule.get('name')
                rule.access = security_rule.get('access')
                rule.protocol = security_rule.get('protocol')
                rule.direction = security_rule.get('direction')
                rule.description = security_rule.get('description')
                rule.source_port_ranges = security_rule.get('sourcePortRanges')
                rule.source_addresses = security_rule.get('sourceAddressPrefixes')
                rule.destination_addresses = security_rule.get('destinationAddressPrefixes')

                port_ranges = security_rule.get('destinationPortRanges') or []
                if security_rule.get('destinationPortRange'):
                    port_ranges.append(security_rule.get('destinationPortRange'))
                rule.destination_port_ranges = port_ranges

                rules.append(rule)
            except Exception:
                logger.exception(f'Failed fetching security rule for {security_rule}')

        return rules

    @staticmethod
    def _parse_ip_ranges(ip_ranges: list):
        ip_v4_ranges = []
        ip_v6_ranges = []
        for ip_range in ip_ranges:
            if ip_range.get('ipRanges') and isinstance(ip_range.get('ipRanges'), list):
                ip_v4_ranges.extend(ip_range.get('ipRanges') or [])
            if ip_range.get('ipv4Ranges') and isinstance(ip_range.get('ipv4Ranges'), dict):
                for ip_v4 in ip_range.get('ipv4Ranges'):
                    if ip_v4.get('cidrIp'):
                        ip_v4_ranges.append(ip_v4.get('cidrIp'))
            if ip_range.get('ipv6Ranges') and isinstance(ip_range.get('ipv6Ranges'), dict):
                for ip_v6 in ip_range.get('ipv6Ranges'):
                    if ip_v6.get('cidrIp'):
                        ip_v6_ranges.append(ip_v6.get('cidrIp'))

        return ip_v4_ranges, ip_v6_ranges

    @staticmethod
    def _fill_security_groups_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            security_group = SecurityGroup()

            security_group.url = device_raw.get('url')
            security_group.account = device_raw.get('account')
            security_group.resource_type = device_raw.get('resourceType')

            if device_raw.get('data') and isinstance(device_raw.get('data'), dict):
                device_raw_data = device_raw.get('data')

                security_group.vpc_id = device_raw_data.get('vpcId')
                security_group.group_id = device_raw_data.get('groupId')
                security_group.owner_id = device_raw_data.get('ownerId')
                security_group.group_name = device_raw_data.get('groupName')
                security_group.description = device_raw_data.get('description')

                if device_raw_data.get('ipPermissions') and isinstance(device_raw_data.get('ipPermissions'), list):
                    ip_v4_ranges_in, ip_v6_ranges_in = PrismaCloudAdapter._parse_ip_ranges(
                        device_raw_data.get('ipPermissions'))
                    if ip_v4_ranges_in:
                        security_group.ip_v4_ranges_in = ip_v4_ranges_in
                    if ip_v6_ranges_in:
                        security_group.ip_v6_ranges_in = ip_v6_ranges_in

                if device_raw_data.get('ipPermissionsEgress') and isinstance(device_raw_data.get('ipPermissionsEgress'),
                                                                             list):
                    ip_v4_ranges_out, ip_v6_ranges_out = PrismaCloudAdapter._parse_ip_ranges(
                        device_raw_data.get('ipPermissionsEgress'))
                    if ip_v4_ranges_out:
                        security_group.ip_v4_ranges_out = ip_v4_ranges_out
                    if ip_v6_ranges_out:
                        security_group.ip_v6_ranges_out = ip_v6_ranges_out

                rules = []
                if device_raw_data.get('securityRules') and isinstance(device_raw_data.get('securityRules'), list):
                    rules.extend(PrismaCloudAdapter._parse_security_rules(device_raw_data.get('securityRules')))

                if device_raw_data.get('defaultSecurityRules') and isinstance(
                        device_raw_data.get('defaultSecurityRules'), list):
                    rules.extend(PrismaCloudAdapter._parse_security_rules(device_raw_data.get('defaultSecurityRules')))

                security_group.security_rules = rules

            device.security_group = security_group
            device.last_seen = parse_date(device_raw.get('lastSeen'))
        except Exception:
            logger.exception(f'Failed creating security group instance for device {device_raw}')

    @staticmethod
    def _fill_shared_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            shared_fields = SharedFields()

            shared_fields.account_id = device_raw.get('accountId')
            shared_fields.account_name = device_raw.get('accountName')
            shared_fields.cloud_type = device_raw.get('cloudType')
            shared_fields.region_id = device_raw.get('regionId')
            shared_fields.region_name = device_raw.get('regionName')
            shared_fields.service = device_raw.get('service')
            shared_fields.deleted = device_raw.get('deleted')
            shared_fields.has_network = device_raw.get('hasNetwork')

            device.shared_fields = shared_fields
        except Exception:
            logger.exception(f'Failed creating shared fields for device {device_raw}')

    def _create_device(self, device_raw: dict, device_type, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('rrn')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.cloud_id = device_raw.get('id')
            device.name = device_raw.get('name')
            device.description = device_raw.get('description')
            device.cloud_provider = device_type

            self._fill_shared_fields(device_raw, device)

            if device_type == CloudInstances.SECURITYGROUP.value:
                self._fill_security_groups_fields(device_raw, device)
            elif device_raw.get('data') and isinstance(device_raw.get('data'), dict):
                if device_type == CloudInstances.AWS.value:
                    self._fill_ec2_fields(device_raw.get('data'), device)
                elif device_type == CloudInstances.AZURE.value:
                    self._fill_azure_fields(device_raw.get('data'), device)
                elif device_type == CloudInstances.GCP.value:
                    self._fill_gcp_fields(device_raw.get('data'), device)

            device.set_raw(device_raw)
            return device

        except Exception:
            logger.exception(f'Problem with fetching PrismaCloud Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            if not device_raw or not device_type:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, device_type, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with parsing device_raw {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
