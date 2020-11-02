import logging
from typing import Tuple

from aws_adapter.connection.structures import OnlyAWSDeviceAdapter, AWS_POWER_STATE_MAP, AWSRole, AWSEBSVolume
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceRunningState
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import normalize_var_name
from azure_adapter.consts import POWER_STATE_MAP
from azure_adapter.structures import AzureImage
from g_naapi_adapter.connection import GNaapiConnection
from g_naapi_adapter.client_id import get_client_id
from g_naapi_adapter.structures import GNaapiDeviceInstance, GNaapiUserInstance, GNaapiRelationships, \
    GNAApiDeviceType, GEIXComputeServer, GNaapiAzureDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-branches, too-many-statements
class GNaapiAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(GNaapiDeviceInstance):
        pass

    class MyUserAdapter(GNaapiUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(
            client_config.get('domain'), https_proxy=client_config.get('https_proxy')
        )

    @staticmethod
    def get_connection(client_config):
        connection = GNaapiConnection(
            domain=client_config['domain'],
            apikey=client_config['api_key'],
            verify_ssl=client_config['verify_ssl'],
            https_proxy=client_config.get('https_proxy')
        )
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
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema GNaapiAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Domain',
                    'type': 'string'
                },
                {
                    'name': 'api_key',
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
                'api_key',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _create_aws_ec2(device_raw: dict, aws_device: OnlyAWSDeviceAdapter, device: MyDeviceAdapter):
        """
        A lot of Copy paste from aws_ec2_eks_ecs_elb.py
        :return:
        """
        aws_device.aws_device_type = 'EC2'
        device.hostname = device_raw.get('publicDnsName') or device_raw.get('privateDnsName')
        power_state = AWS_POWER_STATE_MAP.get(device_raw.get('state', {}).get('name'),
                                              DeviceRunningState.Unknown)

        device.power_state = power_state
        try:
            tags_dict = {i['key']: i['value'] for i in device_raw.get('tags', {})}
        except Exception:
            logger.exception(f'Problem parsing tags dict')
            tags_dict = {}
        for key, value in tags_dict.items():
            aws_device.add_aws_ec2_tag(key=key, value=value)
        aws_device.instance_type = device_raw['instanceType']
        aws_device.key_name = device_raw.get('keyName')
        vpc_id = device_raw.get('vpcId')
        if vpc_id and isinstance(vpc_id, str):
            vpc_id = vpc_id.lower()
            aws_device.vpc_id = vpc_id
        subnet_id = device_raw.get('SubnetId')
        if subnet_id:
            aws_device.subnet_id = subnet_id
        device.name = tags_dict.get('Name', '')

        try:
            device.figure_os(device_raw.get('platform', ''))
        except Exception:
            logger.exception(f'Problem parsing OS type')

        aws_device.private_dns_name = device_raw.get('privateDnsName')
        aws_device.public_dns_name = device_raw.get('publicDnsName')
        try:
            aws_device.monitoring_state = (device_raw.get('monitoring') or {}).get('state')
        except Exception:
            logger.exception(f'Problem getting monitoring state for {device_raw}')

        try:
            for security_group in (device_raw.get('securityGroups') or []):
                aws_device.add_aws_security_group(
                    name=security_group.get('groupName')
                )
        except Exception:
            logger.exception(f'Problem getting security groups at {device_raw}')

        ec2_ips = []
        for iface in device_raw.get('networkInterfaces', []):
            ec2_ips = [addr.get('privateIpAddress') for addr in iface.get('privateIpAddresses', [])]

            assoc = iface.get('association')
            if assoc is not None:
                public_ip = assoc.get('publicIp')
                if public_ip:
                    device.add_public_ip(public_ip)
                    ec2_ips.append(public_ip)

            device.add_nic(iface.get('macAddress'), ec2_ips)

        more_ips = []

        specific_private_ip_address = device_raw.get('privateIpAddress')
        if specific_private_ip_address:
            if specific_private_ip_address not in ec2_ips:
                more_ips.append(specific_private_ip_address)

        specific_public_ip_address = device_raw.get('publicIpAddress')
        if specific_public_ip_address and specific_public_ip_address not in ec2_ips:
            more_ips.append(specific_public_ip_address)
            device.add_public_ip(specific_public_ip_address)

        if more_ips:
            device.add_ips_and_macs(ips=more_ips)

        try:
            aws_device.launch_time = parse_date(device_raw.get('launchTime'))
        except Exception:
            logger.exception(f'Problem getting launch time for {device_raw}')
        aws_device.image_id = device_raw.get('imageId')

        try:
            iam_instance_profile_raw = device_raw.get('iamInstanceProfile')
            if iam_instance_profile_raw:
                aws_device.aws_attached_role = AWSRole(
                    role_id=iam_instance_profile_raw.get('id'),
                    role_arn=iam_instance_profile_raw.get('arn')
                )
        except Exception:
            logger.exception(f'Could not parse iam instance profile')

        try:
            for ebs in (device_raw.get('blockDeviceMappings') or []):
                aws_device.ebs_volumes.append(
                    AWSEBSVolume(
                        name=ebs.get('deviceName'),
                        volume_id=ebs.get('ebs', {}).get('volumeId'),
                    )
                )
        except Exception:
            logger.exception(f'Error parsing instance volumes')

    # pylint: disable=too-many-locals
    @staticmethod
    def _create_device_azure(device_raw: dict, azure_device: GNaapiAzureDeviceInstance, device: MyDeviceAdapter):
        properties = device_raw.get('properties') or device_raw.get('Properties')
        if not isinstance(properties, dict):
            logger.error('Error - Azure device properties is not a dict')
            return

        device.name = device_raw.get('name')
        device.device_managed_by = device_raw.get('managedBy')
        azure_device.resources_group = device_raw.get('resourceGroup')
        azure_device.subscription_id = device_raw.get('subscriptionId')
        azure_device.tenant_id = device_raw.get('tenantId')
        azure_device.plan = device_raw.get('plan')
        azure_device.location = device_raw.get('location')

        instance_view = (device_raw.get('extended') or {}).get('instanceView') or {}
        power_state_code = (instance_view.get('powerState') or {}).get('code')
        if isinstance(power_state_code, str):
            device.power_state = POWER_STATE_MAP.get(power_state_code)

        azure_device.vm_id = properties.get('vmId')
        device.cloud_id = properties.get('vmId')

        storage_profile = properties.get('storageProfile') or {}
        network_profile = properties.get('networkProfile') or {}
        hardware_profile = properties.get('hardwareProfile') or {}
        os_profile = properties.get('osProfile') or {}

        os_profile.pop('secrets', None)     # pop secrets

        azure_device.instance_type = hardware_profile.get('vmSize')
        image = storage_profile.get('imageReference') or {}
        os_disk = storage_profile.get('osDisk') or {}
        os_info = []

        if os_disk:
            os_info.append(os_disk.get('osType'))
            managed_disk_id = (os_disk.get('managedDisk') or {}).get('id')
            if managed_disk_id:
                device.add_hd(description=managed_disk_id)

        if image:
            image_id = image.get('id')
            if isinstance(image_id, str) and '/images/' in image_id:
                azure_device.custom_image_name = image_id[image_id.find('/images/') + len('/images/'):].split('/')[0]

            azure_device.image = AzureImage(publisher=image.get('publisher'),
                                            offer=image.get('offer'),
                                            sku=image.get('sku'),
                                            version=image.get('version'),
                                            exact_version=image.get('exactVersion'))
            os_info.extend([image.get('offer'), image.get('sku'), image.get('exactVersion')])

        if instance_view and isinstance(instance_view, dict):
            if instance_view.get('osName'):
                os_info.append(str(instance_view.get('osName')))
            if instance_view.get('osVersion'):
                os_info.append(str(instance_view.get('osVersion')))

        device.figure_os(' '.join([v for v in os_info if v is not None]))

        for disk in (storage_profile.get('datadisks') or []):
            # add also the attached HDs
            if disk.get('diskSizeGB'):
                device.add_hd(total_size=disk.get('diskSizeGB'))

        device.hostname = os_profile.get('computerName')
        azure_device.admin_username = os_profile.get('adminUsername')

        axonius_extended = device_raw.get('axonius_extended') or {}
        nics_extended = axonius_extended.get('microsoft/network/networkinterfaces') or []

        for iface in nics_extended:
            ips = []
            subnets = []
            for ip_config_d in iface.get('ipConfigurations', []):
                ip_config = ip_config_d.get('properties') or {}
                private_ip = ip_config.get('privateIPAddress')
                if private_ip:
                    ips.append(private_ip)
                public_ip = ip_config.get('publicIpAddress', {}).get('ipAddress')
                if not public_ip:
                    public_ip = ip_config.get('publicIPAddress', {}).get('ipAddress')
                if public_ip:
                    ips.append(public_ip)
                    device.add_public_ip(public_ip)
                try:
                    if ip_config.get('subnet', {}).get('addressPrefix'):
                        subnets.append(ip_config.get('subnet', {}).get('addressPrefix'))
                except Exception:
                    pass
                subnet_id = ip_config.get('subnet', {}).get('id')
                try:
                    if isinstance(subnet_id, str) and '/virtualNetworks/' in subnet_id:
                        device.virtual_networks.append(subnet_id[subnet_id.find('/virtualNetworks/') +
                                                                 len('/virtualNetworks/'):].split('/')[0])
                except Exception:
                    pass
            device.add_nic(
                mac=iface.get('macAddress'), ips=[ip for ip in ips if ip is not None],
                subnets=[subnet for subnet in subnets if subnet is not None],
                name=iface.get('name') or iface.get('id')
            )

    @staticmethod
    def _create_device_geix(device_raw: dict, geix_device: GEIXComputeServer, device: MyDeviceAdapter):
        resource = device_raw.get('Resource') or device_raw.get('resource')
        if not isinstance(resource, dict):
            logger.error(f'Error - GEIX with no "Resource"')
            return

        # pop secrets
        device_raw.pop('admin_password', None)

        geix_device.region = device_raw.get('Region')
        geix_device.account_id = device_raw.get('AccountId')
        geix_device.account_alias = device_raw.get('AccountAlias')

        addresses = resource.get('addresses')
        if isinstance(addresses, dict):
            for address_in in addresses.values():
                if isinstance(address_in, list):
                    for nic in address_in:
                        mac = nic.get('OS-EXT-IPS-MAC:mac_addr')
                        ip = nic.get('addr')

                        if mac or ip:
                            device.add_nic(mac=mac, ips=([ip] if ip else None))

        device.description = resource.get('description')
        geix_device.host_id = resource.get('host_id')
        geix_device.host_status = resource.get('host_status')
        device.cloud_id = resource.get('id')
        geix_device.created_at = parse_date(resource.get('created_at'))
        geix_device.availability_zone = resource.get('availability_zone')
        geix_device.instance_name = resource.get('instance_name')
        geix_device.key_name = resource.get('key_name')
        geix_device.project_id = resource.get('project_id')
        geix_device.vm_state = resource.get('vm_state')

        metadata = resource.get('metadata') or {}
        geix_device.owner_name = metadata.get('owner_name')
        device.device_managed_by = metadata.get('owner_name')

    def _create_device(self, device_raw_tuple: Tuple[dict, GNAApiDeviceType], device: MyDeviceAdapter):
        try:
            device_raw: dict = device_raw_tuple[0]
            device_type: GNAApiDeviceType = device_raw_tuple[1]

            device_id = device_raw.get('ResourceId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.g_naapi_index_date = parse_date(device_raw.get('IndexDate'))
            device.g_naapi_ttl = parse_date(device_raw.get('TTL'))
            device.g_naapi_source = device_raw.get('NaapiSource')
            device.harvest_date = parse_date(device_raw.get('harvest_date'))

            tags = device_raw.get('Tags') or {}
            relationships = device_raw.get('Relationships') or []
            try:
                for relationship in relationships:
                    device.relationships.append(
                        GNaapiRelationships(
                            relationship_name=relationship.get('RelationshipName'),
                            resource_id=relationship.get('ResourceId'),
                            resource_name=relationship.get('ResourceName'),
                            resource_type=relationship.get('ResourceType'),
                        )
                    )
            except Exception:
                logger.exception(f'Could not parse relationships')

            if device_type == GNAApiDeviceType.AWSEC2:
                device.cloud_provider = 'AWS'
                device.cloud_id = device_id
                configuration = device_raw.get('configuration') or device_raw.get('Configuration')
                if not configuration:
                    logger.warning(f'Bad device with no configuration: {configuration}')
                    return None
                aws_info = OnlyAWSDeviceAdapter()
                self._create_aws_ec2(configuration, aws_info, device)

                try:
                    if device_raw.get('awsAccountAlias'):
                        aws_info.aws_account_alias.append(device_raw.get('awsAccountAlias'))
                    aws_info.aws_account_id = device_raw.get('awsAccountId') or device_raw.get('AccountId')
                    aws_info.aws_region = device_raw.get('AwsRegion')
                    aws_info.aws_availability_zone = device_raw.get('AvailabilityZone')
                    aws_info.instance_arn = device_raw.get('Arn')
                except Exception:
                    logger.exception(f'Problem appending extra info')

                    # Things that come from the root json (aws config info)
                    if tags.get('Name'):
                        device.name = tags.get('Name')

                device.aws_data = aws_info

            elif device_type == GNAApiDeviceType.AzureCompute:
                device.cloud_provider = 'Azure'
                if not device_raw.get('properties') and not device_raw.get('Properties'):
                    logger.warning(f'Bad Azure device with no properties')
                    return None

                azure_data = GNaapiAzureDeviceInstance()
                self._create_device_azure(device_raw, azure_data, device)
                device.azure_data = azure_data
            elif device_type == GNAApiDeviceType.GEIXCompute:
                device.cloud_provider = 'GEIX'
                device.cloud_id = device_id
                if not device_raw.get('resource') and not device_raw.get('Resource'):
                    logger.warning(f'Bad GEIX device with no properties')
                    return None

                geix_data = GEIXComputeServer()
                self._create_device_geix(device_raw, geix_data, device)
                device.geix_data = geix_data

            try:
                try:
                    tags_dict = {i['key']: i['value'] for i in device_raw.get('tags', {})}
                except Exception:
                    logger.exception(f'Problem parsing tags dict')
                    tags_dict = {}

                if not tags_dict and isinstance(tags, dict):
                    tags_dict = tags
                for key, value in tags_dict.items():
                    key = key.lower()
                    device.add_key_value_tag(key=key, value=value)

                    if self.__tags_to_parse_as_fields and key.strip() in self.__tags_to_parse_as_fields:
                        normalized_key_name = 'tag_naapi_' + normalize_var_name(key.strip())
                        if not device.does_field_exist(normalized_key_name):
                            cn_capitalized = ' '.join([word.capitalize() for word in key.strip().split(' ')])
                            device.declare_new_field(normalized_key_name, Field(str, f'Naapi Tag {cn_capitalized}'))

                        device[normalized_key_name] = str(value)
            except Exception:
                logger.exception(f'Failed adding tags')

            device.g_naapi_configuration_item_capture_time = parse_date(device_raw.get('ConfigurationItemCaptureTime'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching GNaapi Device')
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
                logger.exception(f'Problem with fetching GNaapi Device for {device_raw}')

    @staticmethod
    def _create_user(user_raw: dict, user: MyUserAdapter):
        return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        """
        Gets raw data and yields User objects.
        :param users_raw_data: the raw data we get.
        :return:
        """
        for user_raw in users_raw_data:
            if not user_raw:
                continue
            try:
                # noinspection PyTypeChecker
                user = self._create_user(user_raw, self._new_user_adapter())
                if user:
                    yield user
            except Exception:
                logger.exception(f'Problem with fetching GNaapi User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'list_of_tags_to_parse_as_fields',
                    'title': 'List of tags to parse as fields',
                    'type': 'string'
                }
            ],
            'required': [],
            'pretty_name': 'NAAPI Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'list_of_tags_to_parse_as_fields': None
        }

    def _on_config_update(self, config):
        self.__tags_to_parse_as_fields = [
            x.strip().lower() for x in config.get('list_of_tags_to_parse_as_fields').split(',')
        ] if isinstance(config.get('list_of_tags_to_parse_as_fields'), str) else None
