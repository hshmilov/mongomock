import logging

from aws_adapter.connection.structures import OnlyAWSDeviceAdapter, AWS_POWER_STATE_MAP, AWSRole, AWSEBSVolume
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceRunningState
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from g_naapi_adapter.connection import GNaapiConnection
from g_naapi_adapter.client_id import get_client_id
from g_naapi_adapter.structures import GNaapiDeviceInstance, GNaapiUserInstance, GNaapiRelationships

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-branches, too-many-statements
class GNaapiAdapter(AdapterBase):
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
            device.add_key_value_tag(key, value)
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

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('ResourceId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.cloud_id = device_id
            device.cloud_provider = 'AWS'
            device.g_naapi_index_date = parse_date(device_raw.get('IndexDate'))
            device.g_naapi_ttl = parse_date(device_raw.get('TTL'))

            configuration = device_raw.get('configuration') or device_raw.get('Configuration')
            if not configuration:
                logger.exception(f'Bad device with no configuration: {configuration}')
                return None
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
                logger.exception(f'Could not parse relatnionships')

            aws_info = OnlyAWSDeviceAdapter()
            self._create_aws_ec2(configuration, aws_info, device)

            # Things that come from the root json (aws config info)
            if tags.get('Name'):
                device.name = tags.get('Name')

            try:
                if device_raw.get('awsAccountAlias'):
                    aws_info.aws_account_alias.append(device_raw.get('awsAccountAlias'))
                aws_info.aws_account_id = device_raw.get('awsAccountId') or device_raw.get('AccountId')
                aws_info.aws_region = device_raw.get('AwsRegion')
                aws_info.aws_availability_zone = device_raw.get('AvailabilityZone')
                aws_info.instance_arn = device_raw.get('Arn')
            except Exception:
                logger.exception(f'Problem appending extra info')

            device.last_seen = parse_date(device_raw.get('ConfigurationItemCaptureTime'))
            device.aws_data = aws_info
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching GNaapi Device for {device_raw}')
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
