import logging
import os
import re
import base64
import subprocess
import json
import functools

import boto3
import kubernetes
import botocore.exceptions
from botocore.config import Config

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import (AdapterException,
                                        ClientConnectionException,
                                        CredentialErrorException)
from axonius.devices.device_adapter import DeviceRunningState
from axonius.devices.device_or_container_adapter import DeviceOrContainerAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


AWS_ACCESS_KEY_ID = 'aws_access_key_id'
REGION_NAME = 'region_name'
AWS_SECRET_ACCESS_KEY = 'aws_secret_access_key'
AWS_SESSION_TOKEN = 'aws_session_token'
AWS_CONFIG = 'config'
ACCOUNT_TAG = 'account_tag'
ROLES_TO_ASSUME_LIST = 'roles_to_assume_list'
PROXY = 'proxy'
GET_ALL_REGIONS = 'get_all_regions'
REGIONS_NAMES = ['us-west-2', 'us-west-1', 'us-east-2', 'us-east-1', 'ap-south-1', 'ap-northeast-2', 'ap-southeast-1',
                 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'cn-north-1', 'eu-central-1', 'eu-west-1',
                 'eu-west-2', 'eu-west-3', 'sa-east-1', 'us-gov-west-1']
PAGE_NUMBER_FLOOD_PROTECTION = 9000


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


def get_paginated_next_token_api(func):
    next_token = None
    page_number = 0

    while page_number < PAGE_NUMBER_FLOOD_PROTECTION:
        page_number += 1
        if next_token:
            result = func(nextToken=next_token)
        else:
            result = func()

        yield result

        next_token = result.get('nextToken')
        if not next_token:
            break


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
    described_vpcs = ec2_client.describe_vpcs()
    vpc_dict = {}

    for vpc_raw in described_vpcs['Vpcs']:
        vpc_id = vpc_raw['VpcId']
        vpc_tags = dict()

        for vpc_tag_raw in (vpc_raw.get('Tags') or []):
            try:
                vpc_tags[vpc_tag_raw['Key']] = vpc_tag_raw['Value']
            except Exception:
                logger.exception(f'Error while parsing vpc tag {vpc_tag_raw}')

        vpc_dict[vpc_id] = vpc_tags.get('Name')

    # make a dictionary from ami key to the value
    return vpc_dict


class AWSTagKeyValue(SmartJsonClass):
    """ A definition for a key value field"""
    key = Field(str, 'AWS Tag Key')
    value = Field(str, 'AWS Tag Value')


class AWSIPRule(SmartJsonClass):
    from_port = Field(int, 'From Port')
    to_port = Field(int, 'To Port')
    ip_protocol = Field(str, 'IP Protocol')
    ip_ranges = ListField(str, 'CIDR')


class AWSSecurityGroup(SmartJsonClass):
    name = Field(str, 'Security Group Name')
    inbound = ListField(AWSIPRule, 'Inbound Rules')
    outbound = ListField(AWSIPRule, 'Outbound Rules')


class AwsAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceOrContainerAdapter):
        account_tag = Field(str, 'Account Tag')
        aws_region = Field(str, 'Region')
        aws_source = Field(str, 'Source')    # Specifiy if it is from a user, a role, or what.
        aws_availability_zone = Field(str, 'Availability Zone')
        aws_device_type = Field(str, 'Device Type (EC2/ECS/EKS)', enum=['EC2', 'ECS', 'EKS'])
        security_groups = ListField(AWSSecurityGroup, 'Security Groups')

        # EC2-specific fields
        public_ip = Field(str, 'Public IP')
        aws_tags = ListField(AWSTagKeyValue, 'Tags')
        instance_type = Field(str, 'Instance Type')
        key_name = Field(str, 'Key Name')
        monitoring_state = Field(str, 'Monitoring State')

        # VPC Generic Fields
        subnet_id = Field(str, 'Subnet Id')
        subnet_name = Field(str, 'Subnet Name')
        vpc_id = Field(str, 'VPC Id')
        vpc_name = Field(str, 'VPC Name')

        # ECS / EKS specific fields
        container_instance_arn = Field(str, 'Task ContainerInstance ID/ARN')
        ecs_device_type = Field(str, 'ECS Launch Type', enum=['Fargate', 'EC2'])
        ecs_ec2_instance_id = Field(str, "ECS EC2 Instance ID")
        ecs_ami_id = Field(str, "ECS Host Ami-ID")

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
        # We are going to change client_config throughout the function so copy it first
        client_config = client_config.copy()

        # Lets start with getting all parameters and validating them.
        if client_config.get(ROLES_TO_ASSUME_LIST):
            roles_to_assume_file = self._grab_file_contents(client_config[ROLES_TO_ASSUME_LIST]).decode('utf-8')
        else:
            roles_to_assume_file = ''
        roles_to_assume_list = []
        roles_temp_credentials = {}

        if (client_config.get(GET_ALL_REGIONS) or False) is True and client_config[REGION_NAME]:
            raise ClientConnectionException(f'Please specify a region name or select all regions, '
                                            f'but not both of them')

        # Input validation
        failed_arns = []
        pattern = re.compile('^arn:aws:iam::[0-9]+:role\/.*')
        if roles_to_assume_file:
            for role_arn in roles_to_assume_file.strip().split(','):
                role_arn = role_arn.strip()
                # A role must look like 'arn:aws:iam::[account_id]:role/[name_of_role]
                # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html#genref-arns
                if not pattern.match(role_arn):
                    failed_arns.append(role_arn)
                roles_to_assume_list.append(role_arn)

        # Handle proxy settings
        https_proxy = client_config.get(PROXY)
        if https_proxy:
            logger.info(f'Setting proxy {https_proxy}')
            client_config[AWS_CONFIG] = Config(proxies={'https': https_proxy})

        # Check if we have some failures
        if len(failed_arns) > 0:
            raise ClientConnectionException(
                f'Invalid role arns found. Please specify a comma-delimited list of valid role arns. '
                f'Invalid arns: {", ".join(failed_arns)}')

        # Get all the temporary credentials for this role
        for role_arn in roles_to_assume_list:
            try:
                # for each role, we have to create a new session in which we are logged in with the current IAM
                # user. if we try to assume two roles one after the other we would have a mixed set of privileges.
                current_session = boto3.Session(
                    aws_access_key_id=client_config[AWS_ACCESS_KEY_ID],
                    aws_secret_access_key=client_config[AWS_SECRET_ACCESS_KEY],
                )
                sts_client = current_session.client('sts', config=client_config.get(AWS_CONFIG))
                assumed_role_object = sts_client.assume_role(
                    RoleArn=role_arn,
                    DurationSeconds=60 * 60 * 3,    # 3 hours of a session
                    RoleSessionName="Axonius"
                )

                roles_temp_credentials[role_arn] = assumed_role_object['Credentials']
            except Exception as e:
                logger.exception(f'Error while assuming role {role_arn}')
                # We prefer showing this message one by one because we want to show the exception.
                # If we would have shown all failed roles at once this would be a huge string...
                raise ClientConnectionException(f'Can not assume role {role_arn}: {str(e)}')

        clients_dict = {}

        if (client_config.get(GET_ALL_REGIONS) or False) is False:
            if not client_config.get(REGION_NAME):
                raise ClientConnectionException('No region was chosen')

            input_region_name = str(client_config.get(REGION_NAME)).lower()
            if input_region_name not in REGIONS_NAMES:
                raise ClientConnectionException(f'region name {input_region_name} does not exist!')
            regions_to_pull_from = [input_region_name]
        else:
            regions_to_pull_from = REGIONS_NAMES

        # We want to fail only if we failed connecting to everything we can
        aws_access_key_id = client_config[AWS_ACCESS_KEY_ID]
        successful_connections = []
        failed_connections = []
        for region in regions_to_pull_from:
            # we need to get the data for this IAM account and for the roles applied.
            current_client_config = client_config.copy()
            current_client_config[REGION_NAME] = region

            current_try = f'IAM User {aws_access_key_id} with region {region}'
            try:
                clients_dict[f'IAM_User_{aws_access_key_id}_{region}'] = \
                    self._connect_client_by_source(current_client_config)
                successful_connections.append(current_try)
            except Exception as e:
                logger.exception(f'Problem with iam user for region {region}')
                failed_connections.append(f'{current_try}: {str(e)}')

            for role_arn, role_credentials in roles_temp_credentials.items():
                # Note! using the same client_config or current_client_config will result in an error since
                # we are changing this dict, which is in use by the reuslt of self._connect_client_by_source!
                # thus, eks for example, could get later different credentials than it needs.
                # so always have a .copy() here!
                current_try = f'IAM Role {role_arn} with region {region}'
                current_client_config = client_config.copy()
                current_client_config[REGION_NAME] = region
                current_client_config[AWS_ACCESS_KEY_ID] = role_credentials['AccessKeyId']
                current_client_config[AWS_SECRET_ACCESS_KEY] = role_credentials['SecretAccessKey']
                current_client_config[AWS_SESSION_TOKEN] = role_credentials['SessionToken']

                try:
                    clients_dict[f'IAM_Role_{role_arn}_{region}'] = \
                        self._connect_client_by_source(current_client_config)
                    successful_connections.append(current_try)
                except Exception as e:
                    logger.exception(f'problem with role {role_arn} for region {region}')
                    failed_connections.append(f'{current_try}: {str(e)}')

        if len(successful_connections) == 0:
            # If none has succeeded, its usually when the IAM user has an error. In that case we must show
            # an error message, but we can not show all of them since this will result in a huge string.
            # we show the first one which usually indicates the problem.
            raise ClientConnectionException(f'Failed connecting to aws: {failed_connections[0]}')

        if len(failed_connections) > 0:
            connections_failures = ', '.join(failed_connections)
            total_connections = len(successful_connections) + len(failed_connections)
            self.create_notification(
                f'AWS Adapter connected to {len(successful_connections)} / {total_connections} successfully.',
                content=f'Failed connections: {connections_failures}' if len(connections_failures) > 0 else '')

        return clients_dict

    def _connect_client_by_source(self, client_config):
        try:
            params = dict()
            params[REGION_NAME] = client_config[REGION_NAME]
            params[AWS_ACCESS_KEY_ID] = client_config[AWS_ACCESS_KEY_ID]
            params[AWS_SECRET_ACCESS_KEY] = client_config[AWS_SECRET_ACCESS_KEY]
            params[AWS_CONFIG] = client_config.get(AWS_CONFIG)
            params[AWS_SESSION_TOKEN] = client_config.get(AWS_SESSION_TOKEN)

            boto3_client_ec2 = None
            boto3_client_ecs = None
            boto3_client_eks = None
            try:
                boto3_client_ec2 = boto3.client('ec2', **params)
            except botocore.exceptions.BotoCoreError as e:
                message = 'Could not create EC2 client for account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            except botocore.exceptions.ClientError as e:
                message = 'Error connecting to EC2 client with account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            try:
                boto3_client_ecs = boto3.client('ecs', **params)
            except botocore.exceptions.BotoCoreError as e:
                message = 'Could not create ECS client for account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            except botocore.exceptions.ClientError as e:
                message = 'Error connecting to ECS client with account {0}, reason: {1}'.format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            try:
                boto3_client_eks = boto3.client('eks', **params)
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
                # we have got plenty of errors, lets show at least the ec2 part. this usually means credentials issue.
                raise ClientConnectionException(f'Could not connect to AWS EC2 or ECS or EKS services: {errors["ec2"]}')
            else:
                # Stores both EC2 and EKS clients in a dict
                if client_config.get(ACCOUNT_TAG):
                    boto3_clients['account_tag'] = client_config.get(ACCOUNT_TAG)
                if errors.get('ec2') is None:
                    boto3_clients['ec2'] = boto3_client_ec2
                if errors.get('ecs') is None:
                    boto3_clients['ecs'] = boto3_client_ecs
                if errors.get('eks') is None:
                    boto3_clients['eks'] = boto3_client_eks
                # Store the credentials in the client_config as well as we need them in the future for token generation
                boto3_clients['credentials'] = client_config
                boto3_clients['region'] = params[REGION_NAME]
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
        parsed_data = {}
        for source, client_data_by_source in client_data.items():
            try:
                parsed_data[source] = self._query_devices_by_client_by_source(client_data_by_source)
            except Exception:
                logger.exception(f'Problem querying source {source}')
        return parsed_data

    def _query_devices_by_client_by_source(self, client_data):
        """
        Get all AWS (EC2 & EKS) instances from a specific client

        :param str client_name: the name of the client as returned from _get_clients
        :param client_data: The data of the client, as returned from the _parse_clients_data function
            if there is EC2 data, client_data['ec2'] will contain that data
            if there is EKS data, client_data['eks'] will contain that data
        :return: http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.describe_instances
        """
        raw_data = {}
        raw_data['account_tag'] = client_data.get('account_tag')
        raw_data['region'] = client_data.get('region')
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
                    logger.exception('Could not describe aws images')

                try:
                    described_vpcs = _describe_vpcs_from_client(ec2_client_data)
                except Exception:
                    described_vpcs = {}
                    logger.exception('Could not describe aws vpcs')

                # add image and vpc information to each instance
                for reservation in reservations:
                    for instance in reservation['Instances']:
                        instance['DescribedImage'] = described_images.get(instance['ImageId'])

                security_groups_dict = dict()
                try:
                    for security_group_raw_answer in get_paginated_next_token_api(
                            ec2_client_data.describe_security_groups):
                        for security_group in security_group_raw_answer['SecurityGroups']:
                            if security_group.get('GroupId'):
                                security_groups_dict[security_group.get('GroupId')] = security_group

                except Exception:
                    logger.exception(f'Problem getting security_groups')

                subnets_dict = dict()
                try:
                    for subnet_raw in ec2_client_data.describe_subnets()['Subnets']:
                        subnet_id = subnet_raw['SubnetId']
                        subnet_tags = dict()
                        for subnet_tag_raw in (subnet_raw.get('Tags') or []):
                            try:
                                subnet_tags[subnet_tag_raw['Key']] = subnet_tag_raw['Value']
                            except Exception:
                                logger.exception(f'problem parsing {subnet_tag_raw}')

                        subnets_dict[subnet_id] = {
                            'name': subnet_tags.get('Name'),
                            'vpc_id': subnet_raw.get('VpcId')
                        }
                except Exception:
                    logger.exception(f'could not parse subnets')

                raw_data['ec2'] = reservations
                raw_data['vpcs'] = described_vpcs
                raw_data['security_groups'] = security_groups_dict
                raw_data['subnets'] = subnets_dict
            except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError,
                    botocore.exceptions.CredentialRetrievalError, botocore.exceptions.UnknownCredentialError) as e:
                raise CredentialErrorException(repr(e))
            except botocore.exceptions.BotoCoreError as e:
                raise AdapterException(repr(e))
        # Checks whether client_data contains ECS data
        if client_data.get('ecs') is not None:
            try:
                raw_data['ecs'] = []
                ecs_client_data = client_data.get('ecs')

                # First, list active clusters. We set the pagination by ourselves since we have to describe these
                # clusters to see which is currently active, and list_clusters has a limit of 100.

                clusters = dict()
                for clusters_raw in get_paginated_next_token_api(
                        functools.partial(ecs_client_data.list_clusters, maxResults=100)):
                    for cluster in ecs_client_data.describe_clusters(clusters=clusters_raw['clusterArns'])['clusters']:
                        try:
                            if cluster['status'].lower() == 'active':
                                clusters[cluster['clusterArn']] = cluster
                        except Exception:
                            logger.exception(f'Error parsing cluster {cluster}')

                for cluster_arn, cluster_data in clusters.items():
                    # Tasks can run on Fargate or on ec2. We have to get all info about ec2 instances beforehand. the maximum
                    # number describe_container_instances can query is 100, by their API.
                    try:
                        container_instances = dict()
                        for containers_instances_raw in get_paginated_next_token_api(
                                functools.partial(ecs_client_data.list_container_instances, maxResults=100,
                                                  cluster=cluster_arn)):
                            try:
                                containerInstanceArns = containers_instances_raw['containerInstanceArns']
                                if containerInstanceArns:
                                    for container_instance in \
                                            ecs_client_data.describe_container_instances(
                                                cluster=cluster_arn,
                                                containerInstances=containerInstanceArns
                                            )['containerInstances']:
                                        container_instance_arn = container_instance.get('containerInstanceArn')
                                        if container_instance_arn:
                                            container_instances[container_instance_arn] = container_instance
                            except Exception:
                                logger.exception(f'Problem in describe container instances {containers_instances_raw} ')

                        # Services has limit of 10, its the only one.
                        services = dict()
                        for services_raw in get_paginated_next_token_api(
                                functools.partial(ecs_client_data.list_services, maxResults=10, cluster=cluster_arn)
                        ):
                            try:
                                service_arns = services_raw['serviceArns']
                                if service_arns:
                                    for service_raw in ecs_client_data.describe_services(
                                            cluster=cluster_arn,
                                            services=service_arns)['services']:
                                        service_name = service_raw.get('serviceName')
                                        if service_name:
                                            services[service_name] = service_raw
                            except Exception:
                                logger.exception(f'Problem describe_services for {services_raw}')

                        # Next, we list all tasks in this cluster. Like before, describe_tasks is limited to 100 so we set
                        # the pagination to this.
                        all_tasks = []
                        for tasks_arns_raw in get_paginated_next_token_api(
                                functools.partial(ecs_client_data.list_tasks, maxResults=100, cluster=cluster_arn)):
                            try:
                                task_arns = tasks_arns_raw['taskArns']
                                if task_arns:
                                    all_tasks += \
                                        ecs_client_data.describe_tasks(
                                            cluster=cluster_arn, tasks=task_arns)['tasks']
                            except Exception:
                                logger.exception(f'Problem describing tasks {tasks_arns_raw}')

                        # Finally just append everything into this cluster containers
                        raw_data['ecs'].append((cluster_data, container_instances, services, all_tasks))
                    except Exception:
                        logger.exception(f'Problem parsing cluster {cluster_arn} with data {cluster_data}')
            except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError,
                    botocore.exceptions.CredentialRetrievalError, botocore.exceptions.UnknownCredentialError) as e:
                raise CredentialErrorException(repr(e))
            except botocore.exceptions.BotoCoreError as e:
                raise AdapterException(repr(e))
            except Exception:
                raw_data['ecs'] = {}
                # We do not raise an exception here since this could be a networking exception or a programming
                # exception and we do not want the whole adapter to crash.
                logger.exception('Error while parsing ecs')
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

                        endpoint = response['cluster']['endpoint']
                        ca_cert = response['cluster']['certificateAuthority']['data']
                        cluster_name = response['cluster']['name']

                        # We must get the token from the aws-iam-authenticator binary
                        my_env = os.environ.copy()
                        my_env['AWS_ACCESS_KEY_ID'] = client_data['credentials'][AWS_ACCESS_KEY_ID]
                        my_env['AWS_SECRET_ACCESS_KEY'] = client_data['credentials'][AWS_SECRET_ACCESS_KEY]

                        aws_iam_authenticator_process = subprocess.Popen(
                            ['aws-iam-authenticator', 'token', '-i', cluster_name],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            env=my_env
                        )

                        # This should be almost immediate, we put here 30 just to be sure.
                        try:
                            stdout, stderr = aws_iam_authenticator_process.communicate(timeout=30)
                        except subprocess.TimeoutExpired:
                            aws_iam_authenticator_process.kill()
                            raise ValueError(f'Maximum timeout reached for aws-iam-authenticator')

                        if aws_iam_authenticator_process.returncode != 0:
                            raise ValueError(f'error: aws-iam-authenticator return code is '
                                             f'{aws_iam_authenticator_process.returncode}, '
                                             f'stdout: {stdout}\nstderr: {stderr}')

                        api_token = json.loads(stdout.strip())

                        try:
                            api_token = api_token['status']['token']
                        except Exception:
                            raise ValueError(f'Wrong response: {api_token}')

                        # Now we have to write the ca cert to the disk to be able to pass this to kubernetes
                        ca_cert_path = os.path.join(os.path.expanduser('~'), f'{cluster_name}_ca_cert')
                        with open(ca_cert_path, 'wb') as f:
                            f.write(base64.b64decode(ca_cert))

                        try:
                            configuration = kubernetes.client.Configuration()
                            configuration.host = endpoint
                            configuration.ssl_ca_cert = ca_cert_path
                            configuration.api_key['authorization'] = 'Bearer ' + api_token

                            v1 = kubernetes.client.CoreV1Api(kubernetes.client.ApiClient(configuration))
                            ret = v1.list_pod_for_all_namespaces(watch=False)
                            raw_data['eks'][cluster_name] = (response['cluster'], ret.items)
                        finally:
                            os.remove(ca_cert_path)

                    except Exception:
                        logger.exception(f'Could not get cluster info for {cluster}')
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
                    'name': ACCOUNT_TAG,
                    'title': 'Account Tag',
                    'type': 'string'

                },
                {
                    'name': PROXY,
                    'title': 'Proxy',
                    'type': 'string'
                },
                {
                    "name": ROLES_TO_ASSUME_LIST,
                    "title": "Roles to assume",
                    "description": "A list of roles to assume",
                    "type": "file"
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
        for aws_source, devices_raw_data_by_source in devices_raw_data.items():
            try:
                yield from self._parse_raw_data_inner(devices_raw_data_by_source, aws_source)
            except Exception:
                logger.exception(f'Problem parsing data from source {aws_source}')

    def _parse_raw_data_inner(self, devices_raw_data, aws_source):
        aws_region = devices_raw_data.get('region')
        account_tag = devices_raw_data.get('account_tag')
        subnets_by_id = devices_raw_data.get('subnets')
        vpcs_by_id = devices_raw_data.get('vpcs')
        security_group_dict = devices_raw_data.get('security_groups')

        ec2_id_to_ips = dict()

        # Checks whether devices_raw_data contains EC2 data
        if devices_raw_data.get('ec2') is not None:
            ec2_devices_raw_data = devices_raw_data.get('ec2')

            for reservation in ec2_devices_raw_data:
                for device_raw in reservation.get('Instances', []):
                    device = self._new_device_adapter()
                    device.aws_source = aws_source
                    device.aws_region = aws_region
                    device.account_tag = account_tag
                    device.aws_device_type = 'EC2'
                    device.hostname = device_raw.get('PublicDnsName')
                    tags_dict = {i['Key']: i['Value'] for i in device_raw.get('Tags', {})}
                    for key, value in tags_dict.items():
                        device.add_aws_ec2_tag(key=key, value=value)
                        device.add_key_value_tag(key, value)
                    device.instance_type = device_raw['InstanceType']
                    device.key_name = device_raw.get('KeyName')
                    vpc_id = device_raw.get('VpcId')
                    if vpc_id and isinstance(vpc_id, str):
                        vpc_id = vpc_id.lower()
                        device.vpc_id = vpc_id
                        device.vpc_name = vpcs_by_id.get(vpc_id)
                    subnet_id = device_raw.get('SubnetId')
                    if subnet_id:
                        device.subnet_id = subnet_id
                        device.subnet_name = (subnets_by_id.get(subnet_id) or {}).get('name')
                    device.name = tags_dict.get('Name', '')
                    device.figure_os(device_raw['DescribedImage'].get('Description', '')
                                     if device_raw['DescribedImage'] is not None
                                     else device_raw.get('Platform'))
                    device_id = device_raw['InstanceId']
                    device.id = device_id
                    try:
                        device.monitoring_state = (device_raw.get('Monitoring') or {}).get('State')
                    except Exception:
                        logger.exception(f'Problem getting monitoring state for {device_raw}')
                    try:
                        for security_group in device_raw.get('SecurityGroups'):
                            def __make_ip_rules_list(ip_pemissions_list):
                                ip_rules = []
                                if not isinstance(ip_pemissions_list, list):
                                    return None
                                for ip_pemission in ip_pemissions_list:
                                    if not isinstance(ip_pemission, dict):
                                        continue
                                    from_port = int(ip_pemission.get('FromPort')) \
                                        if ip_pemission.get('FromPort') is not None else None
                                    to_port = int(ip_pemission.get('ToPort')) \
                                        if ip_pemission.get('ToPort') is not None else None
                                    ip_protocol = str(ip_pemission.get('IpProtocol')) \
                                        if ip_pemission.get('IpProtocol') else None
                                    if ip_protocol == '-1':
                                        ip_protocol = 'Any'
                                    ip_ranges_raw = ip_pemission.get('IpRanges') or []
                                    ip_ranges_raw_v6 = ip_pemission.get('Ipv6Ranges') or []
                                    ip_ranges_raw += ip_ranges_raw_v6
                                    ip_ranges = []
                                    for ip_range_raw in ip_ranges_raw:
                                        ip_ranges.append((ip_range_raw.get('CidrIp') or '') +
                                                         (ip_range_raw.get('CidrIpv6') or '') +
                                                         '_Description:' + (ip_range_raw.get('Description') or ''))
                                    ip_rules.append(AWSIPRule(from_port=from_port,
                                                              to_port=to_port,
                                                              ip_protocol=ip_protocol,
                                                              ip_ranges=ip_ranges))
                                return ip_rules

                            security_group_raw = security_group_dict.get(security_group.get('GroupId'))
                            if security_group_raw and isinstance(security_group_raw, dict):
                                device.add_aws_security_group(name=security_group.get('GroupName'),
                                                              outbound=__make_ip_rules_list(
                                                                  security_group_raw.get('IpPermissionsEgress')),
                                                              inbound=__make_ip_rules_list(
                                                                  security_group_raw.get('IpPermissions')))
                            else:
                                device.add_aws_security_group(name=security_group.get('GroupName'))
                    except Exception:
                        logger.exception(f'Problem getting security groups at {device_raw}')
                    device.cloud_id = device_raw['InstanceId']
                    device.cloud_provider = 'AWS'

                    ec2_ips = []
                    for iface in device_raw.get('NetworkInterfaces', []):
                        ec2_ips = [addr.get('PrivateIpAddress') for addr in iface.get('PrivateIpAddresses', [])]

                        assoc = iface.get('Association')
                        if assoc is not None:
                            public_ip = assoc.get('PublicIp')
                            if public_ip:
                                device.public_ip = public_ip
                                ec2_ips.append(public_ip)

                        device.add_nic(iface.get('MacAddress'), ec2_ips)

                    if ec2_ips:
                        ec2_id_to_ips[device_id] = ec2_ips
                    device.power_state = POWER_STATE_MAP.get(device_raw.get('State', {}).get('Name'),
                                                             DeviceRunningState.Unknown)

                    device.set_raw(device_raw)
                    yield device

        try:
            if devices_raw_data.get('eks') is not None:
                for cluster_name, cluster_data in devices_raw_data['eks'].items():
                    eks_raw_data, kub_raw_data = cluster_data
                    vpc_id = (eks_raw_data.get('resourcesVpcConfig') or {}).get('vpcId')
                    if isinstance(vpc_id, str):
                        vpc_id = vpc_id.lower()

                    for pod_raw in kub_raw_data:
                        try:
                            pod_raw = pod_raw.to_dict()
                            pod_spec = (pod_raw.get('spec') or {})
                            pod_status = (pod_raw.get('status') or {})
                            containers_specs = pod_spec.get('containers') or []
                            for container_index, container_raw in enumerate((pod_status.get('container_statuses') or [])):
                                try:
                                    device = self._new_device_adapter()
                                    device_id = container_raw.get('container_id')
                                    if not device_id:
                                        logger.error(f'Error, container with no id: {container_raw}')
                                        continue

                                    device.id = device_id

                                    device.aws_source = aws_source
                                    device.aws_region = aws_region
                                    device.account_tag = account_tag
                                    device.aws_device_type = 'EKS'
                                    device.set_instance_or_node(container_instance_name=(
                                        pod_raw.get('spec') or {}).get('node_name'))
                                    device.vpc_id = vpc_id
                                    device.vpc_name = vpcs_by_id.get(vpc_id)
                                    device.cluster_name = cluster_name
                                    device.cluster_id = eks_raw_data.get('arn')
                                    device.name = container_raw.get('name')

                                    device.container_image = container_raw.get('image_id') or container_raw.get('image')

                                    container_state = container_raw.get('state') or {}
                                    container_state = container_state.get('running') or \
                                        container_state.get('terminated') or \
                                        container_state.get('waiting')

                                    if container_state.get('running'):
                                        device.container_last_status = 'running'
                                    elif container_state.get('terminated'):
                                        device.container_last_status = 'terminated'
                                    elif container_state.get('waiting'):
                                        device.container_last_status = 'waiting'

                                    container_spec = {}
                                    if len(containers_specs) > container_index:
                                        container_spec = containers_specs[container_index]

                                    container_ports = container_spec.get('ports') or []
                                    for container_port_configuration in container_ports:
                                        device.add_network_binding(
                                            container_port=container_port_configuration.get('container_port'),
                                            host_port=container_port_configuration.get('host_port'),
                                            name=container_port_configuration.get('name'),
                                            protocol=container_port_configuration.get('protocol')
                                        )

                                    if pod_status.get('pod_ip'):
                                        device.add_nic(ips=[pod_status.get('pod_ip')])
                                    device.set_raw({
                                        'container_status': container_raw,
                                        'container_spec': container_spec,
                                        'pod': pod_raw
                                    })
                                    yield device
                                except Exception:
                                    logger.exception(f'Error parsing container in pod: {container_raw}. bypassing')
                        except Exception:
                            logger.exception(f'Problem parsing eks pod: {pod_raw}')
        except Exception:
            logger.exception(f'Problem parsing eks data {devices_raw_data.get("eks")}')

        try:
            # clusters contains a list of cluster dicts, each one of them
            # contains the raw data of the cluster, its services, its instances, and its tasks.
            # we start with parsing the instances, then tasks.

            clusters = devices_raw_data.get('ecs') or []
            for cluster_raw in clusters:
                cluster_data, container_instances, services, all_tasks = cluster_raw

                for task_raw in all_tasks:
                    launch_type = task_raw.get('launchType')
                    if not launch_type:
                        logger.error(f'Error! ECS Task with no launch type!')
                        continue
                    launch_type = str(launch_type).lower()

                    task_group = task_raw.get('group')
                    if isinstance(task_group, str) and task_group.startswith('service:'):
                        task_service = services.get(task_group[len('service:'):])
                    else:
                        task_service = None

                    for container_raw in (task_raw.get('containers') or []):
                        device = self._new_device_adapter()
                        container_id = container_raw.get('containerArn')
                        if not container_id:
                            logger.error(f'Error, container does not have id! {container_raw}')
                            continue

                        device.id = container_id
                        device.aws_device_type = 'ECS'
                        device.aws_source = aws_source
                        device.aws_region = aws_region
                        device.account_tag = account_tag
                        device.name = container_raw.get('name')
                        device.cluster_id = cluster_data.get('clusterArn')
                        device.cluster_name = cluster_data.get('clusterName')
                        device.container_last_status = container_raw.get('lastStatus')

                        # Parse network interfaces
                        for network_interface in (container_raw.get('networkInterfaces') or []):
                            try:
                                ipv4_addr = network_interface.get('privateIpv4Address')
                                if isinstance(ipv4_addr, str):
                                    ipv4_addr = [ipv4_addr]

                                device.add_nic(
                                    name=network_interface.get('attachmentId'),
                                    ips=ipv4_addr
                                )
                            except Exception:
                                logger.exception(f'Problem parsing network interface {network_interface}')

                        for network_binding in (container_raw.get('networkBindings') or []):
                            device.add_network_binding(
                                bind_ip=network_binding.get('bindIP'),
                                container_port=network_binding.get('containerPort'),
                                host_port=network_binding.get('hostPort'),
                                protocol=network_binding.get('protocol')
                            )

                        # Parse Task
                        try:
                            try:
                                connectivity_at = parse_date(task_raw.get('connectivityAt'))
                            except Exception:
                                connectivity_at = None
                                logger.exception(f'Could not parse connectivityAt of {task_raw}')
                            try:
                                created_at = parse_date(task_raw.get('createdAt'))
                            except Exception:
                                created_at = None
                                logger.exception(f'Could not parse createdAt')

                            task_arn = task_raw.get('taskArn')
                            task_definition_arn = task_raw.get('taskDefinitionArn')
                            task_name = (task_arn.split('/')[1] if len(task_arn.split('/')) > 1 else task_arn)
                            task_definition_name = task_definition_arn.split('/')[1] \
                                if len(task_definition_arn.split('/')) > 1 else task_definition_arn

                            device.set_task_or_pod(
                                connectivity_at=connectivity_at,
                                created_at=created_at,
                                connectivity=task_raw.get('connectivity'),
                                cpu_units=task_raw.get('cpu'),
                                desired_status=task_raw.get('desiredStatus'),
                                task_group=task_group,
                                task_health_status=task_raw.get('healthStatus'),
                                task_last_status=task_raw.get('lastStatus'),
                                task_launch_type=launch_type,
                                task_memory_in_mb=task_raw.get('memory'),
                                task_name=task_name,
                                task_id=task_arn,
                                task_definition_id=task_definition_arn,
                                task_definition_name=task_definition_name,
                                platform_version=task_raw.get('platformVersion')
                            )
                        except Exception:
                            logger.exception(f'Error setting task for container, task is {task_raw}')

                        # Parse Service
                        if task_service:
                            try:
                                device.set_service(
                                    service_name=task_service.get('serviceName'),
                                    service_id=task_service.get('serviceArn'),
                                    service_status=task_service.get('status')
                                )
                            except Exception:
                                logger.exception(f'Error setting service for container, service is {task_service}')

                        # Parse specific info for ec2/fargate
                        device_vpc_id = None
                        device_subnet_id = None

                        container_instance_raw_data = {}
                        if launch_type == 'ec2':
                            device.ecs_device_type = 'EC2'
                            container_instance_arn = task_raw.get('containerInstanceArn')
                            if container_instance_arn:
                                container_instance_raw_data = container_instances.get(container_instance_arn) or {}
                                try:
                                    ecs_ec2_instance_id = container_instance_raw_data.get('ec2InstanceId')
                                    device.ecs_ec2_instance_id = ecs_ec2_instance_id
                                    device.set_instance_or_node(
                                        container_instance_id=container_instance_arn,
                                    )

                                    for attribute in container_instance_raw_data.get('attributes'):
                                        attribute_name = attribute.get('name')
                                        attribute_value = attribute.get('value')

                                        if not isinstance(attribute_name, str) or not isinstance(attribute_value, str):
                                            continue

                                        attribute_name = attribute_name.lower()
                                        if attribute_name == 'ecs.ami-id':
                                            device.ecs_ami_id = attribute_value

                                        elif attribute_name == 'ecs.vpd-id':
                                            device_vpc_id = attribute_value

                                        elif attribute_name == 'ecs.subnet-id':
                                            device_subnet_id = attribute_value

                                        elif attribute_name == 'ecs.availability-zone':
                                            device.aws_availability_zone = attribute_value

                                        elif attribute_name == 'ecs.instance-type':
                                            device.instance_type = attribute_value

                                        elif attribute_name == 'ecs.os-type':
                                            device.figure_os(attribute_value)

                                    # we have no info of the ip of the container in ec2. we have to get all the ip's
                                    # of this ec2 instance from the ec2 data.
                                    ec2_ips = ec2_id_to_ips.get(ecs_ec2_instance_id)
                                    if ec2_ips:
                                        device.add_nic(ips=ec2_ips)
                                except Exception:
                                    logger.exception(f'Problem parsing specific info for ec2, container instance is '
                                                     f'{container_instance_raw_data}')
                        elif launch_type == 'fargate':
                            device.ecs_device_type = 'Fargate'
                            try:
                                attachments = task_raw.get('attachments') or []
                                attachments = [t for t in attachments if t.get('type') == 'ElasticNetworkInterface']
                                for attachment in attachments:
                                    details_dict = dict()
                                    for det in attachment.get('details'):
                                        try:
                                            details_dict[det['name']] = det['value']
                                        except Exception:
                                            logger.exception(f'problem parsing ecs fargate attachment {det}')

                                    device_subnet_id = details_dict.get('subnetId')
                                    network_interface_id = details_dict.get('networkInterfaceId')
                                    mac_address = details_dict.get('macAddress')
                                    private_ip = details_dict.get('privateIPv4Address')

                                    if private_ip:
                                        private_ip = [private_ip]

                                    device.add_nic(mac=mac_address, ips=private_ip, name=network_interface_id)
                            except Exception:
                                logger.exception(f'Error while parsing Fargate attachments!')
                        else:
                            logger.error(f'Error! ECS Task with unrecognized launch type {launch_type}')
                            continue

                        if device_subnet_id:
                            device.subnet_id = device_subnet_id
                            subnet_info = (subnets_by_id.get(device_subnet_id) or {})
                            if subnet_info:
                                device.subnet_name = subnet_info.get('name')
                                vpc_id = subnet_info.get('vpc_id')
                                if vpc_id:
                                    device_vpc_id = vpc_id
                        if device_vpc_id:
                            device.vpc_id = device_vpc_id
                            device.vpc_name = vpcs_by_id.get(vpc_id)

                        device.set_raw(
                            {
                                'task_raw': task_raw,
                                'container_raw': container_raw,
                                'service': task_service,
                                'container_instance': container_instance_raw_data
                            }
                        )
                        yield device
        except Exception:
            logger.exception(f'Problem parsing ecs data {devices_raw_data.get("ecs")}')

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
