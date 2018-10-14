import logging
import os
import re

import boto3
import botocore.exceptions
from botocore.config import Config
from kubernetes import client, config

from aws_adapter.consts import EKS_YAML_FILE
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import (AdapterException,
                                        ClientConnectionException,
                                        CredentialErrorException)
from axonius.devices.device_adapter import (DeviceAdapter,
                                            DeviceRunningState)
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file

logger = logging.getLogger(f'axonius.{__name__}')


AWS_ACCESS_KEY_ID = 'aws_access_key_id'
REGION_NAME = 'region_name'
AWS_SECRET_ACCESS_KEY = 'aws_secret_access_key'
PROXY = 'proxy'
GET_ALL_REGIONS = 'get_all_regions'
REGIONS_NAMES = ['us-west-2', 'us-west-1', 'us-east-2', 'us-east-1', 'ap-south-1', 'ap-northeast-2', 'ap-southeast-1',
                 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'cn-north-1', 'eu-central-1', 'eu-west-1',
                 'eu-west-2', 'eu-west-3', 'sa-east-1', 'us-gov-west-1']


'''
Matches AWS Instance IDs
'''
AWS_EC2_ID_MATCHER = re.compile('i-[0-9a-fA-F]{17}')

# translation table between AWS values to parsed values
POWER_STATE_MAP = {
    'terminated': DeviceRunningState.TurnedOff,
    'stopped': DeviceRunningState.TurnedOff,
    'running': DeviceRunningState.TurnedOn,
    'pending': DeviceRunningState.TurnedOff,
    'shutting-down': DeviceRunningState.ShuttingDown,
    'stopping': DeviceRunningState.ShuttingDown,
}


def _describe_images_from_client_by_id(ec2_client, amis):
    """
    Described images (by ids) from a specific client by id

    :param ec2_client:
    :param amis list(str): list of image ids to get
    :return dict: image-id -> image
    """

    # the reason I use 'Filters->image-id' and not ImageIds is because if I'd use ImageIds
    # would've raise an exception if an image is not found
    # all images are returned at once so no progress is logged
    described_images = ec2_client.describe_images(Filters=[{'Name': 'image-id', 'Values': list(amis)}])

    # make a dictionary from ami key to the value
    return {image['ImageId']: image for image in described_images['Images']}


def _describe_vpcs_from_client(ec2_client):
    """
    Described VPCS's from specific client

    :param ec2_client: the client (boto3.client('ec2'))
    :return dict: vpc-id -> vpc
    """
    described_images = ec2_client.describe_vpcs()

    # make a dictionary from ami key to the value
    return {vpc['VpcId']: vpc for vpc in described_images['Vpcs']}


class AWSTagKeyValue(SmartJsonClass):
    """ A definition for a key value field"""
    key = Field(str, 'AWS Tag Key')
    value = Field(str, 'AWS Tag Value')


class AWSIPRule(SmartJsonClass):
    from_port = Field(str, 'From Port')
    to_port = Field(str, 'To Port')
    ip_protocol = Field(str, 'IP Protocol')
    ip_ranges = ListField(str, 'CIDR')


class AWSSecurityGroup(SmartJsonClass):
    name = Field(str, 'Security Group Name')
    inbound = ListField(AWSIPRule, 'Inbound Rules')
    outbound = ListField(AWSIPRule, 'Outbound Rules')


class AwsAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        account_tag = Field(str, 'Account Tag')
        aws_region = Field(str, 'AWS Region')
        # EC2-specific fields
        public_ip = Field(str, 'Public IP')
        aws_tags = ListField(AWSTagKeyValue, 'AWS EC2 Tags')
        instance_type = Field(str, 'AWS EC2 Instance Type')
        key_name = Field(str, 'AWS EC2 Key Name')
        vpc_id = Field(str, 'AWS EC2 VPC Id')
        vpc_name = Field(str, 'AWS EC2 VPC Name')
        monitoring_state = Field(str, 'Monitoring State')
        security_groups = ListField(AWSSecurityGroup, 'Security Groups')
        # ECS-specific fields
        subnet_id = Field(str, 'AWS ECS SubnetId')
        cluster_arn = Field(str, 'AWS ECS Cluster Arn')
        cluster_name = Field(str, 'AWS ECS \ EKS Cluster Name')
        task_arn = Field(str, 'AWS ECS Task Arn')
        task_definition_arn = Field(str, 'AWS ECS Task Definition Arn')
        last_status = Field(str, 'AWS ECS Task: Last Status')
        desired_status = Field(str, 'AWS ECS Task: Desired Status')
        launch_type = Field(str, 'AWS ECS Launch Type')
        cpu_units = Field(str, 'AWS ECS CPU Units')
        connectivity = Field(str, 'AWS ECS Connectivity')
        ecs_group = Field(str, 'AWS ECS Group')
        hs_memory = Field(str, 'AWS ECS Hard/Soft Memory')
        ecs_platform_version = Field(str, 'AWS ECS Platform Version')

        def add_aws_ec2_tag(self, **kwargs):
            self.aws_tags.append(AWSTagKeyValue(**kwargs))

        def add_aws_security_group(self, **kwargs):
            self.security_groups.append(AWSSecurityGroup(**kwargs))

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config[AWS_ACCESS_KEY_ID] + client_config.get(REGION_NAME, GET_ALL_REGIONS)

    def _test_reachability(self, client_config):
        raise NotImplementedError

    def _connect_client(self, client_config):
        regions_clients_dict = {}
        if (client_config.get(GET_ALL_REGIONS) or False) is False:
            if not client_config.get(REGION_NAME):
                raise ClientConnectionException('No region was chosen')
            regions_clients_dict[client_config[REGION_NAME]] = self._connect_client_by_region(client_config)
            return regions_clients_dict
        # This varialbe will be false if all the regions will raise exception
        client_ok = False
        region_success = []
        for region_name in REGIONS_NAMES:
            try:
                client_config_region = client_config.copy()
                client_config_region[REGION_NAME] = region_name
                regions_clients_dict[region_name] = self._connect_client_by_region(client_config_region)
                client_ok = True
                region_success.append(region_name)
            except Exception:
                logger.exception(f'Problem with Region {region_name}')
        if client_ok:
            regions_success_str = ','.join(region_success)
            self.create_notification(f'AWS adapter with Access Key: '
                                     f'{client_config[AWS_ACCESS_KEY_ID]} connection status',
                                     content=f'AWS adapter with Access Key: '
                                             f'{client_config[AWS_ACCESS_KEY_ID]} connected successfully '
                                             f'to these regions: {regions_success_str})')
            return regions_clients_dict
        raise ClientConnectionException('All the regions returned error')

    def _connect_client_by_region(self, client_config):
        try:
            params = dict()
            params[REGION_NAME] = client_config[REGION_NAME]
            params[AWS_ACCESS_KEY_ID] = client_config[AWS_ACCESS_KEY_ID]
            params[AWS_SECRET_ACCESS_KEY] = client_config[AWS_SECRET_ACCESS_KEY]

            proxies = dict()
            if PROXY in client_config:
                logger.info(f'Setting proxy {client_config[PROXY]}')
                proxies['https'] = client_config[PROXY]

            aws_config = Config(proxies=proxies)
            boto3_client_ec2 = None
            boto3_client_ecs = None
            boto3_client_eks = None
            try:
                boto3_client_ec2 = boto3.client('ec2', **params, config=aws_config)
            except botocore.exceptions.BotoCoreError as e:
                message = 'Could not create EC2 client for account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            except botocore.exceptions.ClientError as e:
                message = 'Error connecting to EC2 client with account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            try:
                boto3_client_ecs = boto3.client('ecs', **params, config=aws_config)
            except botocore.exceptions.BotoCoreError as e:
                message = 'Could not create ECS client for account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            except botocore.exceptions.ClientError as e:
                message = 'Error connecting to ECS client with account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            try:
                boto3_client_eks = boto3.client('eks', **params, config=aws_config)
            except botocore.exceptions.BotoCoreError as e:
                message = 'Could not create EKS client for account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            except botocore.exceptions.ClientError as e:
                message = 'Error connecting to EKS client with account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)

            # Try to get all the instances. if we have the wrong privileges, it will throw an exception.
            # The only way of knowing if the connection works is to try something. we use DryRun=True (for Ec2),
            # and if it all works then we should get:
            # botocore.exceptions.ClientError: An error occurred (DryRunOperation)
            # when calling the DescribeInstances operation: Request would have succeeded, but DryRun flag is set.
            errors = {}
            try:
                boto3_client_ec2.describe_instances(DryRun=True)
            except Exception as e:
                if e.response['Error'].get('Code') != 'DryRunOperation':
                    message = 'Error creating EC2 client for account {0}, reason: {1}'.format(
                        client_config[AWS_ACCESS_KEY_ID], str(e))
                    logger.warning(message)
                    errors['ec2'] = e
            try:
                boto3_client_ecs.list_clusters()
            except Exception as e:
                message = 'Error creating ECS client for account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
                errors['ecs'] = e
            try:
                boto3_client_eks.list_clusters()
            except Exception as e:
                message = 'Error creating EKS client for account {0}, ' \
                          'reason: {1}'.format(client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
                errors['eks'] = e
            boto3_clients = {}

            # Tests whether both clients fail the connection test
            # and therefore whether the credentials must be incorrect
            if len(errors) == 3:
                # I save the errors but not sure how to display them.
                raise ClientConnectionException('Could not connect to AWS EC2 or ECS or EKS services.')
            else:
                # Stores both EC2 and EKS clients in a dict
                if client_config.get('account_tag'):
                    boto3_clients['account_tag'] = client_config.get('account_tag')
                if errors.get('ec2') is None:
                    boto3_clients['ec2'] = boto3_client_ec2
                if errors.get('ecs') is None:
                    boto3_clients['ecs'] = boto3_client_ecs
                if errors.get('eks') is None:
                    boto3_clients['eks'] = boto3_client_eks
            return boto3_clients
        except botocore.exceptions.BotoCoreError as e:
            message = 'Error creating AWS client for account {0}, reason: {1}'.format(
                client_config[AWS_ACCESS_KEY_ID], str(e))
            logger.exception(message)
        except botocore.exceptions.ClientError as e:
            message = 'Error connecting to client with account {0}, reason: {1}'.format(
                client_config[AWS_ACCESS_KEY_ID], str(e))
            logger.exception(message)
        raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        parsed_data_regions_dict = {}
        for region, client_data_region in client_data.items():
            try:
                parsed_data_regions_dict[region] = self._query_devices_by_client_by_region(client_data[region])
            except Exception:
                logger.exception(f'Problem querying region {region}')
        return parsed_data_regions_dict

    def _query_devices_by_client_by_region(self, client_data):
        """
        Get all AWS (EC2 & EKS) instances from a specific client on a specific region

        :param str client_name: the name of the client as returned from _get_clients
        :param client_data: The data of the client, as returned from the _parse_clients_data function
            if there is EC2 data, client_data['ec2'] will contain that data
            if there is EKS data, client_data['eks'] will contain that data
        :return: http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.describe_instances
        """
        raw_data = {}
        raw_data['account_tag'] = client_data.get('account_tag')
        # Checks whether client_data contains EC2 data
        if client_data.get('ec2') is not None:
            try:
                ec2_client_data = client_data.get('ec2')
                amis = set()
                # all devices are returned at once so no progress is logged
                instances = ec2_client_data.describe_instances()
                reservations = instances['Reservations']
                while instances.get('NextToken'):
                    instances = ec2_client_data.describe_instances(NextToken=instances.get('NextToken'))
                    reservations += instances['Reservations']

                # get all image-ids
                for reservation in reservations:
                    for instance in reservation['Instances']:
                        amis.add(instance['ImageId'])

                try:
                    described_images = _describe_images_from_client_by_id(ec2_client_data, amis)
                except Exception:
                    described_images = {}
                    logger.exception('Couldn\'t describe aws images')

                try:
                    described_vpcs = _describe_vpcs_from_client(ec2_client_data)
                except Exception:
                    described_vpcs = {}
                    logger.exception('Couldn\'t describe aws vpcs')

                # add image and vpc information to each instance
                for reservation in reservations:
                    for instance in reservation['Instances']:
                        instance['DescribedImage'] = described_images.get(instance['ImageId'])
                        instance['VPC'] = described_vpcs.get(instance.get('VpcId'))

                raw_data['ec2'] = reservations
                security_groups_dict = dict()
                try:
                    security_groups_raw = ec2_client_data.describe_security_groups()['SecurityGroups']
                    for security_group in security_groups_raw:
                        if security_group.get('GroupId'):
                            security_groups_dict[security_group.get('GroupId')] = security_group

                except Exception:
                    logger.exception(f'Problemg getting security_groups')
                raw_data['security_groups'] = security_groups_dict
            except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError,
                    botocore.exceptions.CredentialRetrievalError, botocore.exceptions.UnknownCredentialError) as e:
                raise CredentialErrorException(repr(e))
            except botocore.exceptions.BotoCoreError as e:
                raise AdapterException(repr(e))
        # Checks whether client_data contains ECS data
        if client_data.get('ecs') is not None:
            try:
                ecs_client_data = client_data.get('ecs')
                clusters_raw = ecs_client_data.list_clusters()
                clusters = clusters_raw.get('clusterArns')
                while clusters_raw.get('nextToken'):
                    clusters_raw = ecs_client_data.list_clusters(nextToken=clusters_raw.get('nextToken'))
                    clusters += clusters_raw.get('clusterArns')

                tasks_data = []
                for cluster in clusters:
                    try:
                        tasks = ecs_client_data.list_tasks(cluster=cluster)
                        task_arns = tasks.get('taskArns')
                        if task_arns:
                            cluster_tasks_data = ecs_client_data.describe_tasks(cluster=cluster, tasks=task_arns)
                            cluster_tasks_data = cluster_tasks_data.get('tasks')
                            tasks_data.extend(cluster_tasks_data)
                    except Exception:
                        logger.exception(f'Couldn\'t get tasks in cluster {cluster}')

                raw_data['ecs'] = tasks_data
            except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError,
                    botocore.exceptions.CredentialRetrievalError, botocore.exceptions.UnknownCredentialError) as e:
                raise CredentialErrorException(repr(e))
            except botocore.exceptions.BotoCoreError as e:
                raise AdapterException(repr(e))
        # Checks whether client_data contains EKS data
        if client_data.get('eks') is not None:
            try:
                raw_data['eks'] = {}
                eks_client_data = client_data.get('eks')
                clusters_raw = eks_client_data.list_clusters()
                clusters = clusters_raw.get('clusters')
                while clusters_raw.get('nextToken'):
                    clusters_raw = eks_client_data.list_clusters(nextToken=clusters_raw.get('nextToken'))
                    clusters += clusters_raw.get('clusters')

                for cluster in clusters:
                    try:
                        response = eks_client_data.describe_cluster(
                            name=cluster
                        )
                        if response.get('cluster', {}).get('status') != 'ACTIVE':
                            logger.info(f'Non active cluster {cluster}')
                            continue
                        # This opens the file for writing. If it exists, it deletes it first
                        endpoint = response['cluster'].get('endpoint')
                        ca_cert = response['cluster'].get('certificateAuthority').get('data')
                        cluster_name = response['cluster'].get('name')
                        user_path = os.path.expanduser('~')
                        with open(os.path.join(user_path, f'kubectl{cluster}.config'), 'w') as f:
                            f.write(EKS_YAML_FILE.format(endpoint=endpoint, ca_cert=ca_cert, preferences='{}',
                                                         cluster_name=cluster_name))
                        # Configs can be set in Configuration class directly or using helper utility
                        config.load_kube_config(config_file=os.path.join(user_path, f'kubectl{cluster}.config'))
                        v1 = client.CoreV1Api()
                        ret = v1.list_pod_for_all_namespaces(watch=False)
                        raw_data['ecs'][cluster_name] = ret.items
                    except Exception:
                        logger.exception(f'Couldn\'t get descriptions in cluster {cluster}')

            except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError,
                    botocore.exceptions.CredentialRetrievalError, botocore.exceptions.UnknownCredentialError) as e:
                raise CredentialErrorException(repr(e))
            except botocore.exceptions.BotoCoreError as e:
                raise AdapterException(repr(e))
        return raw_data

    def _clients_schema(self):
        """
        The schema AWSAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': REGION_NAME,
                    'title': 'Region Name',
                    'type': 'string'
                },
                {
                    'name': GET_ALL_REGIONS,
                    'title': 'Get All Regions',
                    'type': 'bool'
                },
                {
                    'name': AWS_ACCESS_KEY_ID,
                    'title': 'AWS Access Key ID',
                    'type': 'string'
                },
                {
                    'name': AWS_SECRET_ACCESS_KEY,
                    'title': 'AWS Access Key Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'account_tag',
                    'title': 'Account Tag',
                    'type': 'string'

                },
                {
                    'name': PROXY,
                    'title': 'Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                GET_ALL_REGIONS,
                AWS_ACCESS_KEY_ID,
                AWS_SECRET_ACCESS_KEY
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for region, devices_raw_data_region in devices_raw_data.items():
            try:
                yield from self._parse_raw_data_region(devices_raw_data_region, region)
            except Exception:
                logger.exception(f'Problem parsing data from region {region}')

    def _parse_raw_data_region(self, devices_raw_data, region):
        account_tag = devices_raw_data.get('account_tag')
        # Checks whether devices_raw_data contains EC2 data
        if devices_raw_data.get('ec2') is not None:
            ec2_devices_raw_data = devices_raw_data.get('ec2')
            security_group_dict = devices_raw_data.get('security_groups')
            for reservation in ec2_devices_raw_data:
                for device_raw in reservation.get('Instances', []):
                    device = self._new_device_adapter()
                    device.aws_region = region
                    device.account_tag = account_tag
                    device.hostname = device_raw.get('PublicDnsName')
                    tags_dict = {i['Key']: i['Value'] for i in device_raw.get('Tags', {})}
                    for key, value in tags_dict.items():
                        device.add_aws_ec2_tag(key=key, value=value)
                        device.add_key_value_tag(key, value)
                    device.instance_type = device_raw['InstanceType']
                    device.key_name = device_raw['KeyName']
                    if device_raw.get('VpcId') is not None:
                        device.vpc_id = device_raw['VpcId']
                    if device_raw.get('VPC') is not None:
                        vpc_tags_dict = {i['Key']: i['Value'] for i in device_raw['VPC'].get('Tags', {})}
                        if vpc_tags_dict.get('Name') is not None:
                            device.vpc_name = vpc_tags_dict.get('Name')
                    device.name = tags_dict.get('Name', '')
                    device.figure_os(device_raw['DescribedImage'].get('Description', '')
                                     if device_raw['DescribedImage'] is not None
                                     else device_raw.get('Platform'))
                    device.id = device_raw['InstanceId']
                    try:
                        device.monitoring_state = (device_raw.get('Monitoring') or {}).get('State')
                    except Exception:
                        logger.exception(f'Problem getting monitoring state for {device_raw}')
                    try:
                        for security_group in device_raw.get('SecurityGroups'):
                            def __make_ip_rules_list(ip_pemissions_list):
                                if not isinstance(ip_pemissions_list, list):
                                    return None
                                for ip_pemission in ip_pemissions_list:
                                    if not isinstance(ip_pemission, dict):
                                        continue
                                    from_port = str(ip_pemission.get('FromPort')) \
                                        if ip_pemission.get('FromPort') else None
                                    to_port = str(ip_pemission.get('ToPort')) if ip_pemission.get('ToPort') else None
                                    ip_protocol = str(ip_pemission.get('IpProtocol')) \
                                        if ip_pemission.get('IpProtocol') else None
                                    ip_ranges_raw = (ip_pemission.get('IpRanges') or []).extend(
                                        ip_pemission.get('Ipv6Ranges') or [])
                                    ip_ranges = []
                                    for ip_range_raw in ip_ranges_raw:
                                        ip_ranges.append((ip_range_raw.get('CidrIp') or '') +
                                                         (ip_range_raw.get('CidrIpv6') or '') +
                                                         '_Description:' + (ip_range_raw.get('Description') or ''))
                                    return AWSIPRule(from_port=from_port,
                                                     to_port=to_port,
                                                     ip_protocol=ip_protocol,
                                                     ip_ranges=ip_ranges)
                            security_group_raw = security_group_dict.get(security_group.get('GroupId'))

                            device.add_aws_security_group(name=security_group.get('GroupName'),
                                                          outbound=__make_ip_rules_list(
                                                              security_group_raw.get('IpPermissionsEgress')),
                                                          inbound=__make_ip_rules_list(security_group_raw.get('IpPermissions')))
                    except Exception:
                        logger.exception(f'Problem getting security groups at {device_raw}')
                    device.cloud_id = device_raw['InstanceId']
                    device.cloud_provider = 'AWS'
                    for iface in device_raw.get('NetworkInterfaces', []):
                        assoc = iface.get('Association')
                        if assoc is not None:
                            public_ip = assoc.get('PublicIp')
                            if public_ip:
                                device.public_ip = public_ip
                                device.add_nic(iface.get('MacAddress'), [public_ip])
                        device.add_nic(iface.get('MacAddress'), [addr.get('PrivateIpAddress')
                                                                 for addr in iface.get('PrivateIpAddresses', [])])
                    device.power_state = POWER_STATE_MAP.get(device_raw.get('State', {}).get('Name'),
                                                             DeviceRunningState.Unknown)
                    device.set_raw(device_raw)
                    yield device
        # Checks whether devices_raw_data contains EKS data
        if devices_raw_data.get('eks') is not None:
            eks_devices_raw_data = devices_raw_data.get('eks')
            for cluster_name, cluster_data in eks_devices_raw_data.items():
                try:
                    device = self._new_device_adapter()
                    device.aws_region = region
                    device.account_tag = account_tag
                    device.cluster_name = cluster_name
                    for pod_raw in cluster_data:
                        try:
                            network_interfaces = []
                            nic = dict()
                            nic['ip'] = pod_raw.status.pod_ip
                            network_interfaces.append(nic)
                            device.add_container(name=pod_raw.metadata.namespace + '_' + pod_raw.item.metadata.name,
                                                 network_interfaces=network_interfaces)
                        except Exception:
                            logger.exception(f'Problem with device raw {str(pod_raw)}')
                    device.set_raw({})
                    yield device
                except Exception:
                    logger.exception(f'Problem with {cluster_name}')

        # Checks whether devices_raw_data contains ECS data
        if devices_raw_data.get('ecs') is not None:
            ecs_devices_raw_data = devices_raw_data.get('ecs')
            for device_raw in ecs_devices_raw_data:
                try:
                    device = self._new_device_adapter()
                    device.aws_region = region
                    device.account_tag = account_tag
                    attachments = device_raw.get('attachments')
                    if attachments:
                        try:
                            # There should only be one set of attachments, so attachments is really a list of length 1
                            attachment = attachments[0]
                            if attachment:
                                device.id = attachment['id']  # We want to fail if we don't have an ID
                                device.subnet_id = attachment.get('details')[0]['value']
                                network_interface_id = attachment.get('details')[1]['value']
                                mac_address = attachment.get('details')[2]['value']
                                private_ip = attachment.get('details')[3]['value']
                                device.add_nic(mac=mac_address, ips=[private_ip], name=network_interface_id)
                        except Exception:
                            logger.exception(f'Failed to get attachment data for {device_raw}')
                            continue
                    try:
                        cluster_arn = device_raw.get('clusterArn')
                        if cluster_arn is not None:
                            device.cluster_arn = cluster_arn
                            cluster_name = cluster_arn.split('/')[1]
                            device.cluster_name = cluster_name
                    except Exception:
                        logger.exception(f'Failed to get cluster data for {device_raw}')
                    task_arn = device_raw.get('taskArn')
                    if task_arn:
                        device.task_arn = task_arn
                        device.name = task_arn.split('/')[1] if len(task_arn.split('/')) > 1 else None
                    device.task_definition_arn = device_raw.get('taskDefinitionArn')
                    device.last_status = device_raw.get('lastStatus')
                    device.desired_status = device_raw.get('desiredStatus')
                    device.cpu_units = device_raw.get('cpu')
                    device.launch_type = device_raw.get('launchType')
                    device.connectivity = device_raw.get('connectivity')
                    device.ecs_group = device_raw.get('group')
                    device.hs_memory = device_raw.get('memory')
                    device.ecs_platform_version = device_raw.get('platformVersion')
                    try:
                        containers = device_raw.get('containers')
                        if containers is not None:
                            for container in containers:
                                network_interfaces = []
                                for network_interface in container.get('networkInterfaces'):
                                    nic = dict()
                                    nic['name'] = network_interface.get('attachmentId')
                                    nic['ip'] = network_interface.get('privateIpv4Address')
                                    network_interfaces.append(nic)
                                device.add_container(name=container.get('name'),
                                                     last_status=container.get('lastStatus'),
                                                     network_interfaces=network_interfaces,
                                                     containerArn=container.get('containerArn'))
                    except Exception:
                        logger.exception('Failed to load containers.')
                    device.set_raw(device_raw)
                    yield device
                except Exception as e:
                    logger.exception(f'ERROR: problem loading {device_raw}. Reason: {e}')

    def _correlation_cmds(self):
        """
        Correlation commands for AWS
        :return: shell commands that help collerations
        """

        # AWS assures us that http://169.254.169.254/latest/meta-data/instance-id will return the instance id
        # of the AWS EC2 instance requesting it.
        # http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html

        # This will probably fail on Windows XP because it doesn't have Powershell, hopefully we won't
        # encounter Windows XP that's hosted on AWS (ugh...)
        return {
            'Linux': 'curl http://169.254.169.254/latest/meta-data/instance-id',
            'Windows': 'powershell -Command & ' +
                       'Invoke-RestMethod -uri http://169.254.169.254/latest/meta-data/instance-id'
        }

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        Parses (very easily) the correlation cmd result, or None if failed
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        return next(iter(AWS_EC2_ID_MATCHER.findall(correlation_cmd_result.strip())), None)

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
