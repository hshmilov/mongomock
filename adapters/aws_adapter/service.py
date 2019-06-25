import itertools
import logging
import os
import re
import base64
import subprocess
import json
import functools
import datetime
import socket
from enum import Enum, auto
from typing import Dict, Tuple, List

import boto3
import kubernetes
import botocore.exceptions
from botocore.config import Config
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import (AdapterException,
                                        ClientConnectionException,
                                        CredentialErrorException)
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceRunningState, ShodanVuln
from axonius.devices.device_or_container_adapter import DeviceOrContainerAdapter
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.utils.parsing import format_ip
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.mixins.configurable import Configurable
from axonius.clients.shodan.connection import ShodanConnection

logger = logging.getLogger(f'axonius.{__name__}')


AWS_ACCESS_KEY_ID = 'aws_access_key_id'
REGION_NAME = 'region_name'
AWS_SECRET_ACCESS_KEY = 'aws_secret_access_key'
AWS_SESSION_TOKEN = 'aws_session_token'
AWS_CONFIG = 'config'
ACCOUNT_TAG = 'account_tag'
ROLES_TO_ASSUME_LIST = 'roles_to_assume_list'
USE_ATTACHED_IAM_ROLE = 'use_attached_iam_role'
PROXY = 'proxy'
GET_ALL_REGIONS = 'get_all_regions'
REGIONS_NAMES = ['us-west-2', 'us-west-1', 'us-east-2', 'us-east-1', 'ap-south-1', 'ap-northeast-2', 'ap-southeast-1',
                 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'cn-north-1', 'eu-central-1', 'eu-west-1',
                 'eu-west-2', 'eu-west-3', 'sa-east-1', 'us-gov-west-1', 'ap-east-1', 'eu-north-1', 'us-gov-east-1']
PAGE_NUMBER_FLOOD_PROTECTION = 9000
AWS_ENDPOINT_FOR_REACHABILITY_TEST = f'https://apigateway.us-east-2.amazonaws.com/'   # endpoint for us-east-2
BOTO3_FILTERS_LIMIT = 100


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


class AwsRawDataTypes(Enum):
    Regular = auto()
    SSM = auto()


class AwsSSMSchemas(Enum):
    Application = 'AWS:Application'
    ComplianceItems = 'AWS:ComplianceItem'
    File = 'AWS:File'
    InstanceDetailedInformation = 'AWS:InstanceDetailedInformation'
    Network = 'AWS:Network'
    PatchSummary = 'AWS:PatchSummary'
    PatchCompliance = 'AWS:PatchCompliance'
    ResourceGroup = 'AWS:ResourceGroup'
    Service = 'AWS:Service'
    WindowsRegistry = 'AWS:WindowsRegistry'
    WindowsRole = 'AWS:WindowsRole'
    WindowsUpdate = 'AWS:WindowsUpdate'


def get_paginated_next_token_api(func):
    next_token = None
    page_number = 0
    next_token_name = None

    while page_number < PAGE_NUMBER_FLOOD_PROTECTION:
        page_number += 1
        if next_token:
            result = func(**{next_token_name: next_token})
        else:
            result = func()

        yield result

        if result.get('nextToken'):
            next_token_name = 'nextToken'
        elif result.get('NextToken'):
            next_token_name = 'NextToken'

        if next_token_name:
            next_token = result.get(next_token_name)
        if not next_token:
            break

    if page_number == PAGE_NUMBER_FLOOD_PROTECTION:
        logger.critical('AWS Pagination: reached page flood protection count')


def get_paginated_marker_api(func):
    marker = None
    marker_name = None
    page_number = 0

    while page_number < PAGE_NUMBER_FLOOD_PROTECTION:
        page_number += 1
        if marker:
            result = func(**{marker_name: marker})
        else:
            result = func()

        yield result

        if result.get('IsTruncated') is True or result.get('isTruncated') is True:
            if result.get('Marker'):
                marker_name = 'Marker'
            elif result.get('marker'):
                marker_name = 'marker'

            if marker_name:
                marker = result.get(marker_name)
            if not marker:
                break
        else:
            break

    if page_number == PAGE_NUMBER_FLOOD_PROTECTION:
        logger.critical('AWS Pagination: reached page flood protection count')


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
    described_images = dict()
    amis = list(amis)

    # Filters are limited, usually with 200. So we batch requests of 100
    for i in range(0, len(amis), BOTO3_FILTERS_LIMIT):
        result = ec2_client.describe_images(Filters=[{'Name': 'image-id', 'Values': amis[i:i + BOTO3_FILTERS_LIMIT]}])
        for image in result['Images']:
            described_images[image['ImageId']] = image

    return described_images


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


class AWSRole(SmartJsonClass):
    role_name = Field(str, 'Name')
    role_arn = Field(str, 'ARN')
    role_id = Field(str, 'ID')
    role_description = Field(str, 'Description')
    role_permissions_boundary_policy_name = Field(str, 'Permissions Boundary Policy')
    role_attached_policies_named = ListField(str, 'Attached Policies')


class AWSLoadBalancer(SmartJsonClass):
    name = Field(str, 'Name')
    dns = Field(str, 'DNS')
    scheme = Field(str, 'Scheme', enum=['internet-facing', 'internal'])
    type = Field(str, 'Type', enum=['classic', 'network', 'application'])
    subnets = ListField(str, 'Subnets')
    lb_protocol = Field(str, 'LB Protocol')
    instance_protocol = Field(str, 'Instance Protocol')
    lb_port = Field(int, 'LB Port')
    instance_port = Field(int, 'Instance Port')
    ips = ListField(str, 'External IPs', converter=format_ip, json_format=JsonStringFormat.ip)
    last_ip_by_dns_query = Field(str, 'Last IP by DNS Query', converter=format_ip, json_format=JsonStringFormat.ip)


class SSMComplianceSummary(SmartJsonClass):
    compliance_type = Field(str, 'Compliance Type')
    status = Field(str, 'Status')
    overall_severity = Field(str, 'Overall Severity')
    last_execution = Field(datetime.datetime, 'Last Execution Time')

    compliant_count = Field(int, 'Compliant Count')
    compliant_critical_count = Field(int, 'Compliant Critical Count')
    compliant_high_count = Field(int, 'Compliant High Count')
    compliant_medium_count = Field(int, 'Compliant Medium Count')
    compliant_low_count = Field(int, 'Compliant Low Count')
    compliant_informational_count = Field(int, 'Compliant Informational Count')
    compliant_unspecified_count = Field(int, 'Compliant Unspecified Count')

    non_compliant_count = Field(int, 'Non Compliant Count')
    non_compliant_critical_count = Field(int, 'Non Compliant Critical Count')
    non_compliant_high_count = Field(int, 'Non Compliant High Count')
    non_compliant_medium_count = Field(int, 'Non Compliant Medium Count')
    non_compliant_low_count = Field(int, 'Non Compliant Low Count')
    non_compliant_informational_count = Field(int, 'Non Compliant Informational Count')
    non_compliant_unspecified_count = Field(int, 'Non Compliant Unspecified Count')


class SSMInfo(SmartJsonClass):
    ping_status = Field(str, 'Ping Status')
    last_ping_date = Field(datetime.datetime, 'Last Ping Date')
    agent_version = Field(str, 'Agent Version')
    is_latest_version = Field(bool, 'Is Latest Version')
    activation_id = Field(str, 'Activation Id')
    registration_date = Field(datetime.datetime, 'Registration Date')
    association_status = Field(str, 'Association Status')
    last_association_execution_date = Field(datetime.datetime, 'Last Association Execution Date')
    last_successful_association_execution_date = Field(datetime.datetime, 'Last Successful Association Execution Date')
    patch_group = Field(str, 'Patch Group')
    baseline_id = Field(str, 'Patch Baseline Id')
    baseline_name = Field(str, 'Patch Baseline Name')
    baseline_description = Field(str, 'Patch Baseline Description')
    compliance_summaries = ListField(SSMComplianceSummary, 'Compliance')


class AwsAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceOrContainerAdapter):
        account_tag = Field(str, 'Account Tag')
        aws_region = Field(str, 'Region')
        aws_source = Field(str, 'Source')    # Specifiy if it is from a user, a role, or what.
        aws_availability_zone = Field(str, 'Availability Zone')
        aws_device_type = Field(
            str,
            'Device Type (EC2/ECS/EKS/ELB/Managed/NAT)',
            enum=['EC2', 'ECS', 'EKS', 'ELB', 'Managed', 'NAT']
        )
        security_groups = ListField(AWSSecurityGroup, 'Security Groups')

        # EC2-specific fields
        aws_tags = ListField(AWSTagKeyValue, 'AWS Tags')
        instance_type = Field(str, 'Instance Type')
        key_name = Field(str, 'Key Name')
        private_dns_name = Field(str, 'Private Dns Name')
        monitoring_state = Field(str, 'Monitoring State')
        launch_time = Field(datetime.datetime, 'Launch Time')
        image_id = Field(str, 'AMI (Image) ID')
        aws_attached_role = Field(AWSRole, 'Attached Role')
        aws_load_balancers = ListField(AWSLoadBalancer, 'Load Balancer (ELB)')

        # VPC Generic Fields
        subnet_id = Field(str, 'Subnet Id')
        subnet_name = Field(str, 'Subnet Name')
        vpc_id = Field(str, 'VPC Id')
        vpc_name = Field(str, 'VPC Name')

        # ECS / EKS specific fields
        container_instance_arn = Field(str, 'Task ContainerInstance ID/ARN')
        ecs_device_type = Field(str, 'ECS Launch Type', enum=['Fargate', 'EC2'])
        ecs_ec2_instance_id = Field(str, "ECS EC2 Instance ID")

        # SSM specific fields
        ssm_data = Field(SSMInfo, 'SSM Information')

        def add_aws_ec2_tag(self, **kwargs):
            self.aws_tags.append(AWSTagKeyValue(**kwargs))

        def add_aws_security_group(self, **kwargs):
            self.security_groups.append(AWSSecurityGroup(**kwargs))

        def add_aws_load_balancer(self, **kwargs):
            self.aws_load_balancers.append(AWSLoadBalancer(**kwargs))

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return (client_config.get(AWS_ACCESS_KEY_ID) or '') + (client_config.get(REGION_NAME) or GET_ALL_REGIONS)

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(AWS_ENDPOINT_FOR_REACHABILITY_TEST)

    def _connect_client(self, original_client_config):
        # Credentials to some of the clients are temporary so we have to re-create them every cycle.
        # So here we must try to connect (if an exception occurs this will change the status of the adapter)
        # but this must occur every cycle.
        client_config = original_client_config.copy()

        has_iam_credentials = client_config.get(AWS_ACCESS_KEY_ID) and client_config.get(AWS_SECRET_ACCESS_KEY)
        has_attached_iam_instance_role = client_config.get(USE_ATTACHED_IAM_ROLE)

        if not has_iam_credentials and not has_attached_iam_instance_role:
            raise ClientConnectionException(f'Please specify credentials or select use attached instance role')

        if has_attached_iam_instance_role:
            # If the user requested to use the attached instance role, ignore the iam credentials.
            client_config.pop(AWS_ACCESS_KEY_ID, None)
            client_config.pop(AWS_SECRET_ACCESS_KEY, None)

        self._connect_client_once(client_config, True)
        return client_config

    def get_assumed_session(self, role_arn: str, region, client_config: dict):
        """STS Role assume a boto3.Session

        With automatic credential renewal.
        Notes: We have to poke at botocore internals a few times
        """
        session_credentials = RefreshableCredentials.create_from_metadata(
            metadata=functools.partial(
                self.boto3_role_credentials_metadata_maker, role_arn, client_config)(),
            refresh_using=functools.partial(
                self.boto3_role_credentials_metadata_maker, role_arn, client_config),
            method='sts-assume-role'
        )
        role_session = get_session()
        role_session._credentials = session_credentials
        role_session.set_config_variable('region', region)
        return boto3.Session(botocore_session=role_session)

    @staticmethod
    def boto3_role_credentials_metadata_maker(role_arn: str, client_config: dict):
        """
        Generates a "metadata" dict creator that is used to initialize auto-refreshing sessions.
        This is done to support auto-refreshing role-sessions; When we assume a role, we have to put a duration
        for it. when it expires, the internal botocore class will auto refresh it. This is the refresh function.
        for more information look at: https://dev.to/li_chastina/auto-refresh-aws-tokens-using-iam-role-and-boto3-2cjf
        :param role_arn: the name of the role to assume
        :param client_config: client_config from _connect_client_once (includes access keys, regions,
                              proxy settings etc)
        :return:
        """
        current_session = boto3.Session(
            aws_access_key_id=client_config.get(AWS_ACCESS_KEY_ID),
            aws_secret_access_key=client_config.get(AWS_SECRET_ACCESS_KEY),
        )
        sts_client = current_session.client('sts', config=client_config.get(AWS_CONFIG))
        assumed_role_object = sts_client.assume_role(
            RoleArn=role_arn,
            DurationSeconds=60 * 15,  # The minimum possible, because we want to support any customer config
            RoleSessionName="Axonius"
        )

        response = assumed_role_object['Credentials']

        credentials = {
            "access_key": response.get("AccessKeyId"),
            "secret_key": response.get("SecretAccessKey"),
            "token": response.get("SessionToken"),
            "expiry_time": response.get("Expiration").isoformat(),
        }
        return credentials

    def _connect_client_once(self, client_config, should_validate: bool):
        """
        Generates credentials and optionally tries to test them
        :param client_config: the configuration from the adapter scheme
        :param should_validate: whether or not validate these credentials. If True, the function will fail if we can
                                not connect to even a single ec2 service.
        :return:
        """
        # We are going to change client_config throughout the function so copy it first
        clients_dict = dict()
        client_config = client_config.copy()

        # Lets start with getting all parameters and validating them.
        if client_config.get(ROLES_TO_ASSUME_LIST):
            roles_to_assume_file = self._grab_file_contents(client_config[ROLES_TO_ASSUME_LIST]).decode('utf-8')
        else:
            roles_to_assume_file = ''
        roles_to_assume_list = []

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

        if (client_config.get(GET_ALL_REGIONS) or False) is False:
            if not client_config.get(REGION_NAME):
                raise ClientConnectionException('No region was chosen')

            input_region_name = str(client_config.get(REGION_NAME)).lower()
            if input_region_name not in REGIONS_NAMES:
                raise ClientConnectionException(f'region name {input_region_name} does not exist!')
            regions_to_pull_from = [input_region_name]
        else:
            regions_to_pull_from = REGIONS_NAMES

        # We want to fail only if we failed connecting to everything we can. So what we do is we try to connect
        # and query the ec2 service which is mendatory for us.
        aws_access_key_id = client_config.get(AWS_ACCESS_KEY_ID) or 'attached_instance_iam_role'
        clients_dict[aws_access_key_id] = dict()
        failed_connections = []
        for region in regions_to_pull_from:
            current_try = f'IAM User {aws_access_key_id} with region {region}'
            permanent_session = boto3.Session(
                aws_access_key_id=client_config.get(AWS_ACCESS_KEY_ID),
                aws_secret_access_key=client_config.get(AWS_SECRET_ACCESS_KEY),
                region_name=region
            )
            clients_dict[aws_access_key_id][region] = permanent_session
            try:
                if should_validate:
                    self._test_ec2_connection(permanent_session, config=client_config.get(AWS_CONFIG))
                    should_validate = False  # if even one connection succeeds, do not check anything else
            except Exception as e:
                logger.exception(f'Problem with iam user for region {region}')
                failed_connections.append(f'{current_try}: {str(e)}')

            for role_arn in roles_to_assume_list:
                try:
                    current_try = f'IAM Role {role_arn} with region {region}'
                    auto_refresh_session = self.get_assumed_session(role_arn, region, client_config)
                    if role_arn not in clients_dict:
                        clients_dict[role_arn] = dict()
                    clients_dict[role_arn][region] = auto_refresh_session
                    try:
                        if should_validate:
                            self._test_ec2_connection(auto_refresh_session, config=client_config.get(AWS_CONFIG))
                            should_validate = False  # if even one connection succeeds, do not check anything else
                    except Exception as e:
                        logger.exception(f'problem with role {role_arn} for region {region}')
                        failed_connections.append(f'{current_try}: {str(e)}')
                except Exception as e:
                    logger.exception(f'Error assuming role {role_arn}')
                    raise ClientConnectionException(f'Error assuming role {role_arn}: {str(e)}')

        # If should_validate remained True, it means nothing has passed any validation.
        # It its False, then something passed validation, or we did not require any.
        if should_validate is True:
            # If none has succeeded, its usually when the IAM user has an error. In that case we must show
            # an error message, but we can not show all of them since this will result in a huge string.
            # we show the first one which usually indicates the problem.
            raise ClientConnectionException(f'Failed connecting to aws: {failed_connections[0]}')

        return clients_dict, client_config

    @staticmethod
    def _test_ec2_connection(session, **extra_params):
        try:
            boto3_client_ec2 = session.client('ec2', **extra_params)
            boto3_client_ec2.describe_instances(DryRun=True)
        except Exception as e:
            if 'Request would have succeeded, but DryRun flag is set.' not in str(e):
                raise

    def _connect_client_by_source(self, session: boto3.Session, region_name: str, client_config: dict):
        params = {AWS_CONFIG: client_config.get(AWS_CONFIG), REGION_NAME: region_name}
        clients = dict()
        errors = dict()

        try:
            c = session.client('ec2', **params)
            c.describe_instances()
            clients['ec2'] = c
        except Exception as e:
            errors['ec2'] = str(e)

        try:
            c = session.client('ecs', **params)
            c.list_clusters()
            clients['ecs'] = c
        except Exception as e:
            errors['ecs'] = str(e)

        try:
            c = session.client('eks', **params)
            c.list_clusters()
            clients['eks'] = c
        except Exception as e:
            if not 'Could not connect to the endpoint URL' in str(e):
                # This means EKS is not supported in this region, this is not an error.
                errors['eks'] = str(e)

        try:
            c = session.client('iam', **params)
            c.list_roles()
            clients['iam'] = c
        except Exception as e:
            errors['iam'] = str(e)

        try:
            c = session.client('elb', **params)
            c.describe_load_balancers()
            clients['elbv1'] = c
        except Exception as e:
            errors['elbv1'] = str(e)

        try:
            c = session.client('elbv2', **params)
            c.describe_load_balancers()
            clients['elbv2'] = c
        except Exception as e:
            errors['elbv2'] = str(e)

        try:
            c = session.client('ssm', **params)
            c.get_inventory_schema()
            clients['ssm'] = c
        except Exception as e:
            errors['ssm'] = str(e)

        # the only service we truely need is ec2. all the rest are optional.
        # If this has failed we raise an exception
        if not clients.get('ec2'):
            raise ClientConnectionException(f'Could not connect: {errors.get("ec2")}')

        clients['account_tag'] = client_config.get(ACCOUNT_TAG)
        clients['credentials'] = client_config
        clients['region'] = params[REGION_NAME]

        return clients, errors

    def _query_devices_by_client(self, client_name, client_data_credentials):
        # we must re-create all credentials (const and temporary)
        https_proxy = client_data_credentials.get(PROXY)
        client_data, client_config = self._connect_client_once(client_data_credentials, False)
        # First, we must get clients for everything we need
        client_data_aws_clients = dict()
        successful_connections = []
        failed_connections = []
        warnings_messages = []
        for account, account_regions_clients in client_data.items():
            if account not in client_data_aws_clients:
                client_data_aws_clients[account] = dict()
            for region_name, client_data_by_region in account_regions_clients.items():
                current_try = f'{account}_{region_name}'
                try:
                    client_data_aws_clients[account][region_name], warnings = \
                        self._connect_client_by_source(client_data_by_region, region_name, client_config)
                    successful_connections.append(current_try)
                    if warnings:
                        for service_name, service_error in warnings.items():
                            error_string = f'{current_try}: {service_name} - {service_error}'
                            logger.warning(error_string)
                            warnings_messages.append(error_string)
                except Exception as e:
                    logger.exception(f'problem with {current_try}')
                    failed_connections.append(f'{current_try}: {str(e)}')

        total_connections = len(successful_connections) + len(failed_connections)
        content = ''
        if len(failed_connections) > 0:
            connections_failures = '\n'.join(failed_connections)
            content = f'Failed connections: \n{connections_failures}\n\n'
        if len(warnings_messages) > 0:
            warnings_str = '\n'.join(warnings_messages)
            content = f'Warnings: \n{warnings_str}'

        if self.__verbose_auth_notifications is True or len(successful_connections) == 0:
            self.create_notification(
                f'AWS Adapter: {len(successful_connections)} / {total_connections} successful connections, '
                f'{len(warnings_messages)} warnings.',
                content=content)

        for account, account_regions_clients in client_data_aws_clients.items():
            logger.info(f'query_devices_by_client account: {account}')
            parsed_data_for_all_regions = None
            for region_name, client_data_by_region in account_regions_clients.items():
                try:
                    source_name = f'{account}_{region_name}'
                    if parsed_data_for_all_regions is None:
                        parsed_data_for_all_regions = self._query_devices_by_client_for_all_sources(
                            client_data_by_region)
                    parse_data_for_source = self._query_devices_by_client_by_source(client_data_by_region,
                                                                                    https_proxy=https_proxy)
                    parse_data_for_source.update(parsed_data_for_all_regions)
                    yield source_name, parse_data_for_source, AwsRawDataTypes.Regular

                    for parse_data_for_source in self._query_devices_by_client_by_source_ssm(
                            client_data_by_region):
                        yield source_name, parse_data_for_source, AwsRawDataTypes.SSM
                except Exception:
                    logger.exception(f'Problem querying source {source_name}')

    def _query_devices_by_client_by_source_ssm(self, client_data):
        extra_data = dict()
        extra_data['account_tag'] = client_data.get('account_tag')
        extra_data['region'] = client_data.get('region')

        if client_data.get('ssm') is not None and self.__fetch_ssm is True:
            try:
                all_instances = dict()
                ssm = client_data['ssm']
                # First, get all instance_id id's that have ssm
                for ssm_page in get_paginated_next_token_api(ssm.describe_instance_information):
                    for instance_information in (ssm_page.get('InstanceInformationList') or []):
                        unique_instance_id = instance_information.get('InstanceId')
                        if unique_instance_id:
                            all_instances[unique_instance_id] = instance_information

                # Next, get all schemas.
                schemas_names = []
                for schema_page in get_paginated_next_token_api(ssm.get_inventory_schema):
                    for schema_raw in schema_page['Schemas']:
                        schema_name = schema_raw.get('TypeName')
                        if schema_name:
                            schemas_names.append(schema_name)

                # Next, get all patch group to patch baseline mappings
                patch_groups_to_patch_baseline = dict()
                try:
                    for patch_group_page in get_paginated_next_token_api(ssm.describe_patch_groups):
                        for patch_group_page_mapping in patch_group_page['Mappings']:
                            try:
                                patch_group_name = patch_group_page_mapping['PatchGroup']
                                patch_groups_to_patch_baseline[patch_group_name] = patch_group_page_mapping
                            except Exception:
                                logger.exception(f'Can not parse patch group page mapping {patch_group_page_mapping}')
                except Exception:
                    logger.exception(f'Problem getting patches')

                # Next, get all compliance summaries
                resource_id_to_compliance_summaries = dict()
                try:
                    for compliance_summary_page in get_paginated_next_token_api(ssm.list_resource_compliance_summaries):
                        for resource_compliance_summary in compliance_summary_page['ResourceComplianceSummaryItems']:
                            try:
                                resource_id = resource_compliance_summary.get('ResourceId')
                                resource_type = resource_compliance_summary.get('ResourceType')
                                if resource_type == 'ManagedInstance' and resource_id:
                                    if resource_id not in resource_id_to_compliance_summaries:
                                        resource_id_to_compliance_summaries[resource_id] = []
                                    resource_id_to_compliance_summaries[resource_id].append(resource_compliance_summary)
                            except Exception:
                                logger.exception(f'Can not parse patch group page mapping {patch_group_page_mapping}')
                except Exception:
                    logger.exception(f'Problem getting complaince summary')

                for iid, iid_basic_data in all_instances.items():
                    raw_instance = dict()
                    raw_instance['basic_data'] = iid_basic_data
                    # Next, pull the following schemas
                    for schema in AwsSSMSchemas:
                        try:
                            entries = []
                            for schema_page in get_paginated_next_token_api(
                                    functools.partial(ssm.list_inventory_entries, InstanceId=iid, TypeName=schema.value)
                            ):
                                entries.extend(schema_page.get('Entries') or [])

                            if entries:
                                raw_instance[schema.value] = entries
                        except Exception:
                            logger.exception(f'Problem querying info of schema {schema.value} for device {iid}')

                    # Also, pull the patches for ths instance
                    all_patches = []
                    try:
                        for patch_page in get_paginated_next_token_api(
                            functools.partial(ssm.describe_instance_patches, InstanceId=iid)
                        ):
                            all_patches.extend(patch_page.get('Patches') or [])

                        if all_patches:
                            raw_instance['patches'] = all_patches
                    except Exception:
                        logger.exception(f'Problem getting patches')

                    # Pull the tags for this resource. This does not support pagination.
                    try:
                        if iid.startswith('mi-'):
                            raw_tags = ssm.list_tags_for_resource(
                                ResourceType='ManagedInstance', ResourceId=iid)['TagList']
                        else:
                            raw_tags = client_data.get('ec2').describe_tags(
                                Filters=[{'Name': 'resource-id', 'Values': [iid]}]
                            )['Tags']

                        raw_instance['tags'] = {item.get('Key'): item.get('Value') for item in raw_tags}
                    except Exception:
                        logger.exception(f'Problem getting ssm tags')

                    # Get compliance summaries
                    raw_instance['compliance_summary'] = resource_id_to_compliance_summaries.get(iid)

                    yield raw_instance, patch_groups_to_patch_baseline, extra_data
            except Exception:
                logger.exception(f'Problem fetching data for ssm')

    def _query_devices_by_client_for_all_sources(self, client_data):
        """
        Sometimes we have to query resources which are relevant for all regions, i.e. IAM which is region-less.
        So instead of doing it for each client we prefer to do it here.
        :param client_data:
        :return:
        """
        raw_data = {}
        logger.info(f'Starting to query devices for region-less aws services')
        # Checks whether client_data contains IAM data
        if client_data.get('iam') is not None and self.__fetch_instance_roles is True:
            try:
                raw_data['instance_profiles'] = {}
                iam_client_data = client_data.get('iam')

                # For each instance that has a role attached to it, we want list all attached policies.
                # So the following code will:
                # 1. list all roles
                # 2. for each roles, list all attached policies (managed & inline)
                # 3. for each role, find all attached instance profiles for it.
                role_i = 0
                for role_answer in get_paginated_marker_api(iam_client_data.list_roles):
                    for role_raw in (role_answer.get('Roles') or []):
                        # Get some basic info about this role
                        role_data = dict()
                        role_name = role_raw.get('RoleName')
                        if not role_name:
                            logger.error(f'Found a role with no role name, continuing: {role_raw}')
                            continue
                        role_i += 1
                        if role_i % 200 == 0:
                            logger.info(f'Parsing role num {role_i}: {role_name}')
                        role_data['role_name'] = role_name
                        if role_raw.get('RoleId'):
                            role_data['role_id'] = role_raw.get('RoleId')
                        if role_raw.get('Arn'):
                            role_data['arn'] = role_raw.get('Arn')
                        if role_raw.get('Description'):
                            role_data['description'] = role_raw.get('Description')

                        get_role_data = iam_client_data.get_role(RoleName=role_name)
                        permissions_boundary_dict = (get_role_data.get('Role') or {}).get('PermissionsBoundary')
                        if permissions_boundary_dict:
                            pb_type = permissions_boundary_dict.get('PermissionsBoundaryType')
                            pb_arn = permissions_boundary_dict.get('PermissionsBoundaryArn')
                            if str(pb_type).lower() == 'policy' and pb_arn:
                                # we have to get the name of this policy
                                try:
                                    policy_name = iam_client_data.get_policy(PolicyArn=pb_arn)['Policy']['PolicyName']
                                    role_data['permissions_boundary_policy_name'] = policy_name
                                except Exception:
                                    logger.exception(f'Could not get policy for permissions boundary arn {pb_arn}, '
                                                     f'continuing')

                        # Now that we have some basic info about the role, lets get all of its attached policies.
                        attached_policies_names = []
                        for attached_policy_answer_raw in get_paginated_marker_api(
                                functools.partial(iam_client_data.list_attached_role_policies, RoleName=role_name)):
                            for attached_policy_raw in (attached_policy_answer_raw.get('AttachedPolicies') or []):
                                if attached_policy_raw.get('PolicyName'):
                                    attached_policies_names.append(attached_policy_raw.get('PolicyName'))

                        for inline_policy_answer_raw in get_paginated_marker_api(
                                functools.partial(iam_client_data.list_role_policies, RoleName=role_name)):
                            attached_policies_names.extend(inline_policy_answer_raw.get('PolicyNames') or [])

                        role_data['attached_policies_names'] = attached_policies_names

                        # Now find all profile instances attached to it
                        for instance_profiles_answer_raw in get_paginated_marker_api(
                                functools.partial(iam_client_data.list_instance_profiles_for_role, RoleName=role_name)
                        ):
                            for instance_profile_raw in (instance_profiles_answer_raw.get('InstanceProfiles') or []):
                                instance_profile_id = instance_profile_raw.get('InstanceProfileId')
                                if instance_profile_id:
                                    if instance_profile_id in raw_data['instance_profiles']:
                                        logger.error(f'Error! instance profile {instance_profile_id} for '
                                                     f'role {role_name} is already in raw data! continuing')
                                        continue
                                    raw_data['instance_profiles'][instance_profile_id] = role_data
            except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError,
                    botocore.exceptions.CredentialRetrievalError, botocore.exceptions.UnknownCredentialError) as e:
                raise CredentialErrorException(repr(e))
            except botocore.exceptions.BotoCoreError as e:
                raise AdapterException(repr(e))
            except Exception:
                # We do not raise an exception here since this could be a networking exception or a programming
                # exception and we do not want the whole adapter to crash.
                logger.exception('Error while parsing iam')

        return raw_data

    def _query_devices_by_client_by_source(self, client_data, https_proxy=None):
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
        region = client_data.get('region')
        raw_data['region'] = region
        logger.info(f'Starting to query devices for region {region}')
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
                try:
                    if self.__shodan_key:
                        shodan_connection = ShodanConnection(apikey=self.__shodan_key, https_proxy=https_proxy)
                        with shodan_connection:
                            for reservation in reservations:
                                for device_raw in reservation.get('Instances', []):
                                    for iface in device_raw.get('NetworkInterfaces', []):
                                        assoc = iface.get('Association')
                                        if assoc is not None:
                                            public_ip = assoc.get('PublicIp')
                                            if public_ip:
                                                try:
                                                    assoc['shodan_info'] = shodan_connection.get_ip_info(public_ip)
                                                except Exception as e:
                                                    if '404' not in str(e):
                                                        logger.exception(f'Problem getting shodan info of {public_ip}')
                except Exception:
                    logger.exception(f'Problem with Shodan')

                nat_gateways = []
                try:
                    if self.__fetch_nat:
                        for nat_gateways_page in get_paginated_next_token_api(ec2_client_data.describe_nat_gateways):
                            nat_gateways.extend(nat_gateways_page.get('NatGateways') or [])
                except Exception:
                    logger.exceptionf('Problem getting NAT Gateways')

                raw_data['ec2'] = reservations
                raw_data['vpcs'] = described_vpcs
                raw_data['security_groups'] = security_groups_dict
                raw_data['subnets'] = subnets_dict
                raw_data['nat'] = nat_gateways
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
                        if client_data['credentials'].get(AWS_ACCESS_KEY_ID):
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
        # Checks whether client_data contains ELB data
        # we declare two dicts. one that maps between instance id's and a list of load balancers that point to them
        # and one that maps between ip's and a list of load balancers that point to them.
        raw_data['elb_by_iid'] = {}
        raw_data['elb_by_ip'] = {}
        raw_data['all_elbs'] = []
        if client_data.get('elbv1') is not None and self.__fetch_load_balancers is True:
            try:
                elbv1_client_data = client_data.get('elbv1')
                elb_num = 0
                for elb_raw_data_answer in get_paginated_marker_api(elbv1_client_data.describe_load_balancers):
                    for elb_raw in (elb_raw_data_answer.get('LoadBalancerDescriptions') or []):
                        elb_dict = {}
                        elb_name = elb_raw.get('LoadBalancerName')
                        if not elb_name:
                            logger.error(f'Error, got load balancer with no name: {elb_raw}, continuing')
                            continue
                        elb_num += 1
                        if elb_num % 200 == 0:
                            logger.info(f'Parsing elb {elb_num}: {elb_name}')

                        elb_dict['name'] = elb_name
                        elb_dict['type'] = 'classic'    # this is elbv1
                        elb_dns_name = elb_raw.get('DNSName')
                        if elb_dns_name:
                            elb_dict['dns'] = elb_dns_name
                            if self.__parse_elb_ips:
                                try:
                                    ip = socket.gethostbyname(elb_dns_name)
                                    if ip:
                                        elb_dict['last_ip_by_dns_query'] = ip
                                except Exception:
                                    logger.exception(f'Could not parse ELB ip for dns {elb_dict}')
                        if elb_raw.get('Scheme'):
                            elb_dict['scheme'] = elb_raw.get('Scheme').lower()
                        if elb_raw.get('Subnets'):
                            elb_dict['subnets'] = elb_raw.get('Subnets')
                        if elb_raw.get('VPCId'):
                            elb_dict['vpcid'] = elb_raw.get('VPCId')
                        if elb_raw.get('SecurityGroups'):
                            elb_dict['security_groups'] = elb_raw.get('SecurityGroups')

                        raw_data['all_elbs'].append(elb_dict)

                        # Get the listeners, i.e. source and dest port
                        for listener_raw in (elb_raw.get('ListenerDescriptions') or []):
                            if not listener_raw.get('Listener'):
                                logger.error(f'Error parsing listener {listener_raw}, continuing')
                                continue
                            lr_data = {}
                            listener_raw_data = listener_raw['Listener']
                            if listener_raw_data.get('Protocol'):
                                lr_data['lb_protocol'] = listener_raw_data.get('Protocol')
                            if listener_raw_data.get('LoadBalancerPort'):
                                lr_data['lb_port'] = listener_raw_data.get('LoadBalancerPort')
                            if listener_raw_data.get('InstanceProtocol'):
                                lr_data['instance_protocol'] = listener_raw_data.get('InstanceProtocol')
                            if listener_raw_data.get('InstancePort'):
                                lr_data['instance_port'] = listener_raw_data.get('InstancePort')
                            # Map this lb to the instances that it points to. Note that for every listener we create
                            # this. This is the format for elbv2 so we do this like this.
                            for elb_instance_raw in elb_raw.get('Instances'):
                                iid = elb_instance_raw.get('InstanceId')
                                if not iid:
                                    logger.error(f'Error pasring elb, no instance id! {elb_raw}, continuing')
                                    continue
                                if iid not in raw_data['elb_by_iid']:
                                    raw_data['elb_by_iid'][iid] = []
                                elb_final_dict = elb_dict.copy()
                                elb_final_dict.update(lr_data)
                                raw_data['elb_by_iid'][iid].append(elb_final_dict)
                logger.debug(f'ELBV1: Parsed {elb_num} elbs.')
            except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError,
                    botocore.exceptions.CredentialRetrievalError, botocore.exceptions.UnknownCredentialError) as e:
                raise CredentialErrorException(repr(e))
            except botocore.exceptions.BotoCoreError as e:
                raise AdapterException(repr(e))
            except Exception:
                # We do not raise an exception here since this could be a networking exception or a programming
                # exception and we do not want the whole adapter to crash.
                logger.exception('Error while parsing ELB v1')
        if client_data.get('elbv2') is not None and self.__fetch_load_balancers is True:
            try:
                elbv2_client_data = client_data.get('elbv2')
                # This one is much more complex than the elbv1 one.
                # we need to query all lb's, then all target groups
                all_elbv2_lbs_by_arn = dict()
                for elbv2_lbs_raw_answer in get_paginated_marker_api(elbv2_client_data.describe_load_balancers):
                    for elbv2_raw_data in (elbv2_lbs_raw_answer.get('LoadBalancers') or []):
                        elbv2_arn = elbv2_raw_data.get('LoadBalancerArn')
                        if not elbv2_arn:
                            logger.error(f'Could not parse elb data for {elbv2_raw_data}, continuing')
                            continue
                        elbv2_data = dict()
                        if elbv2_raw_data.get('LoadBalancerName'):
                            elbv2_data['name'] = elbv2_raw_data.get('LoadBalancerName')
                        elb_dns_name = elbv2_raw_data.get('DNSName')
                        if elb_dns_name:
                            elbv2_data['dns'] = elb_dns_name
                            if self.__parse_elb_ips:
                                try:
                                    ip = socket.gethostbyname(elb_dns_name)
                                    if ip:
                                        elbv2_data['last_ip_by_dns_query'] = ip
                                except Exception:
                                    logger.exception(f'Could not parse ELB ip for dns {elb_dns_name}')
                        if elbv2_raw_data.get('Scheme'):
                            elbv2_data['scheme'] = elbv2_raw_data.get('Scheme').lower()
                        if elbv2_raw_data.get('Type'):
                            elbv2_data['type'] = elbv2_raw_data.get('Type').lower()
                        if elbv2_raw_data.get('VpcId'):
                            elbv2_data['vpcid'] = elbv2_raw_data.get('VpcId')
                        if elbv2_raw_data.get('SecurityGroups'):
                            elbv2_raw_data['security_groups'] = elbv2_raw_data.get('SecurityGroups')
                        elbv2_data['subnets'] = []
                        ip_addresses = []
                        for az_raw in elbv2_raw_data.get('AvailabilityZones') or []:
                            if az_raw.get('SubnetId'):
                                elbv2_data['subnets'].append(az_raw.get('SubnetId'))
                            for lba_raw in az_raw.get('LoadBalancerAddresses') or []:
                                if lba_raw.get('IpAddress'):
                                    ip_addresses.append(lba_raw.get('IpAddress'))
                        if ip_addresses:
                            elbv2_data['ips'] = ip_addresses
                        all_elbv2_lbs_by_arn[elbv2_arn] = elbv2_data
                        raw_data['all_elbs'].append(elbv2_data)

                logger.debug(f'ELBV2: Found {len(all_elbv2_lbs_by_arn)} elbs. Moving to target groups')
                tg_count = 0
                for elbv2_target_groups_answer in get_paginated_marker_api(elbv2_client_data.describe_target_groups):
                    for elbv2_target_group_raw_data in (elbv2_target_groups_answer.get('TargetGroups') or []):
                        tg_arn = elbv2_target_group_raw_data.get('TargetGroupArn')
                        elbv2_tg_lb_arns = elbv2_target_group_raw_data.get('LoadBalancerArns')
                        if not elbv2_tg_lb_arns:
                            # This is a target group which is not assicaoted with any LB
                            continue

                        if not tg_arn:
                            logger.error(f'Error parsing target group, no ARN: {elbv2_target_group_raw_data}, '
                                         f'contuining.')
                            continue
                        tg_count += 1
                        if tg_count % 200 == 0:
                            logger.info(f'Parsing target group {tg_count}: {tg_arn}')
                        tg_type = elbv2_target_group_raw_data.get('TargetType')
                        if not isinstance(tg_type, str) or tg_type.lower() not in ['instance', 'ip']:
                            logger.error(f'Wrong target group type: {tg_type}, continuing')
                            continue
                        tg_type = tg_type.lower()
                        tg_dict = dict()
                        if elbv2_target_group_raw_data.get('Protocol'):
                            # These are the same in new-type lb's.
                            tg_dict['lb_protocol'] = elbv2_target_group_raw_data.get('Protocol')
                            tg_dict['instance_protocol'] = elbv2_target_group_raw_data.get('Protocol')
                        if elbv2_target_group_raw_data.get('Port'):
                            tg_dict['lb_port'] = elbv2_target_group_raw_data.get('Port')

                        elbv2_targets = dict()
                        # For each one of the target groups we must describe all targets.
                        for target_raw in (elbv2_client_data.describe_target_health(TargetGroupArn=tg_arn).get(
                                'TargetHealthDescriptions') or []):
                            target_raw_target = target_raw.get('Target')
                            if not target_raw_target:
                                logger.error(f'Error, no "target" in target health description: {target_raw}, '
                                             f'continuing')
                                continue
                            target_raw_id = target_raw_target.get('Id')
                            target_raw_port = target_raw_target.get('Port')
                            if not target_raw_id or target_raw_port is None:
                                logger.error(f'Error, target_raw is invalid: {target_raw}, continuing')
                                continue
                            final_target_dict = tg_dict.copy()
                            final_target_dict['instance_port'] = target_raw_port
                            if target_raw_id not in elbv2_targets:
                                elbv2_targets[target_raw_id] = []
                                elbv2_targets[target_raw_id].append(final_target_dict)

                        # At this point we have a dict that maps between ip/instance type targets to a partially
                        # built dict that represents an entity. we must add the lb information and then map this
                        # to the final dict of lb's by ip or target.
                        for lb_arn in elbv2_tg_lb_arns:
                            if lb_arn not in all_elbv2_lbs_by_arn:
                                logger.error(f'Error, target group refers to lb {lb_arn} that does not exist, '
                                             f'continuing')
                                continue
                            for final_target_id, final_target_obj_list in elbv2_targets.items():
                                for final_target_obj in final_target_obj_list:
                                    final_lb = all_elbv2_lbs_by_arn[lb_arn].copy()
                                    final_lb.update(final_target_obj)
                                    if tg_type == 'ip':
                                        if final_target_id not in raw_data['elb_by_ip']:
                                            raw_data['elb_by_ip'][final_target_id] = []
                                        raw_data['elb_by_ip'][final_target_id].append(final_lb)
                                    elif tg_type == 'instance':
                                        if final_target_id not in raw_data['elb_by_iid']:
                                            raw_data['elb_by_iid'][final_target_id] = []
                                        raw_data['elb_by_iid'][final_target_id].append(final_lb)

            except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError,
                    botocore.exceptions.CredentialRetrievalError, botocore.exceptions.UnknownCredentialError) as e:
                raise CredentialErrorException(repr(e))
            except botocore.exceptions.BotoCoreError as e:
                raise AdapterException(repr(e))
            except Exception:
                # We do not raise an exception here since this could be a networking exception or a programming
                # exception and we do not want the whole adapter to crash.
                logger.exception('Error while parsing ELB v2')
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
                },
                {
                    'name': USE_ATTACHED_IAM_ROLE,
                    'title': 'Use attached IAM role',
                    'description': 'Use the IAM role attached to this instance instead of using the credentials',
                    'type': 'bool'
                }
            ],
            'required': [
                GET_ALL_REGIONS
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for aws_source, devices_raw_data_by_source, raw_data_type in devices_raw_data:
            try:
                if raw_data_type == AwsRawDataTypes.Regular:
                    yield from self._parse_raw_data_inner_regular(devices_raw_data_by_source, aws_source)
                elif raw_data_type == AwsRawDataTypes.SSM:
                    try:
                        device = self._parse_raw_data_inner_ssm(devices_raw_data_by_source, aws_source)
                        if device:
                            yield device
                    except Exception:
                        logger.exception(f'Problem parsing device from ssm')
                else:
                    logger.critical(f'Can not parse data for aws source {aws_source}, '
                                    f'unknown type {raw_data_type.name}')
            except Exception:
                logger.exception(f'Problem parsing data from source {aws_source}')

    @staticmethod
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

    @staticmethod
    def __add_generic_firewall_rules(device: MyDeviceAdapter, group_name: str, source: str,
                                     direction: str, rule_list: List[AWSIPRule]):
        for rule in rule_list:
            try:
                from_port = rule.from_port
            except Exception:
                from_port = None

            try:
                to_port = rule.to_port
            except Exception:
                to_port = None

            try:
                protocol = rule.ip_protocol
            except Exception:
                protocol = None

            try:
                targets = []
                raw_targets = rule.ip_ranges
                for raw_target in raw_targets:
                    if '_Description:' in raw_target:
                        cidr, desc = raw_target.split('_Description:')
                        final_string = cidr
                        if desc:
                            final_string += f' ({desc})'

                        targets.append(final_string)
                    else:
                        targets.append(raw_target)
            except Exception:
                logger.exception('Problem parsing raw targets')
                targets = []

            for target in targets:
                device.add_firewall_rule(
                    name=group_name,
                    source=source,
                    type='Allow',
                    direction=direction,
                    target=target,
                    protocol=protocol,
                    from_port=from_port,
                    to_port=to_port
                )

    def _parse_raw_data_inner_regular(self, devices_raw_data, aws_source):
        aws_region = devices_raw_data.get('region')
        account_tag = devices_raw_data.get('account_tag')
        subnets_by_id = devices_raw_data.get('subnets') or {}
        vpcs_by_id = devices_raw_data.get('vpcs') or {}
        security_group_dict = devices_raw_data.get('security_groups') or {}
        instance_profiles_dict = devices_raw_data.get('instance_profiles') or {}
        elb_by_ip = devices_raw_data.get('elb_by_ip') or {}
        elb_by_iid = devices_raw_data.get('elb_by_iid') or {}
        all_elbs = devices_raw_data.get('all_elbs') or []
        nat_gateways = devices_raw_data.get('nat') or {}

        ec2_id_to_ips = dict()
        private_ips_to_ec2 = dict()

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
                    device.private_dns_name = device_raw.get('PrivateDnsName')
                    try:
                        device.monitoring_state = (device_raw.get('Monitoring') or {}).get('State')
                    except Exception:
                        logger.exception(f'Problem getting monitoring state for {device_raw}')
                    try:
                        for security_group in (device_raw.get('SecurityGroups') or []):
                            security_group_raw = security_group_dict.get(security_group.get('GroupId'))
                            if security_group_raw and isinstance(security_group_raw, dict):
                                outbound_rules = self.__make_ip_rules_list(
                                    security_group_raw.get('IpPermissionsEgress'))
                                inbound_rules = self.__make_ip_rules_list(security_group_raw.get('IpPermissions'))
                                device.add_aws_security_group(name=security_group.get('GroupName'),
                                                              outbound=outbound_rules,
                                                              inbound=inbound_rules)

                                try:
                                    all_rules_lists = [(outbound_rules, 'EGRESS'), (inbound_rules, 'INGRESS')]
                                    for rule_list, direction in all_rules_lists:
                                        self.__add_generic_firewall_rules(
                                            device,
                                            security_group_raw.get('GroupName'),
                                            'AWS Instance Security Group',
                                            direction,
                                            rule_list
                                        )
                                except Exception:
                                    logger.exception(f'Could not add generic firewall rules')
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
                                device.add_public_ip(public_ip)
                                ec2_ips.append(public_ip)
                                shodan_info = assoc.get('shodan_info')
                                if shodan_info:
                                    shodan_info_data = shodan_info.get('data')
                                    if isinstance(shodan_info_data, dict):
                                        shodan_info_data = [shodan_info_data]
                                    if not isinstance(shodan_info_data, list):
                                        shodan_info_data = []
                                    try:
                                        # shodan info crashed raw_data in the DB for a reason I don't know
                                        assoc.pop('shodan_info', None)
                                        vulns_dict_list = []

                                        if isinstance(shodan_info_data, list):
                                            vulns_dict_list = [shodan_info_data_item.get('vulns')
                                                               for shodan_info_data_item in shodan_info_data
                                                               if isinstance(shodan_info_data_item.get('vulns'), dict)]
                                        vulns = []
                                        for vulns_dict in vulns_dict_list:
                                            for vuln_name, vuln_data in vulns_dict.items():
                                                try:
                                                    vulns.append(ShodanVuln(summary=vuln_data.get('summary'),
                                                                            vuln_name=vuln_name,
                                                                            cvss=float(vuln_data.get('cvss'))
                                                                            if vuln_data.get('cvss') is not None
                                                                            else None))
                                                except Exception:
                                                    logger.exception(f'Problem adding vuln name {vuln_name}')
                                        cpe = []
                                        http_server = None
                                        http_site_map = None
                                        http_location = None
                                        http_security_text_hash = None
                                        for shoda_data_raw in shodan_info_data:
                                            try:
                                                if shoda_data_raw.get('cpe'):
                                                    cpe.extend(shoda_data_raw.get('cpe'))
                                                http_info = shoda_data_raw.get('http')
                                                if http_info and isinstance(http_info, dict):
                                                    if not http_server:
                                                        http_server = http_info.get('server')
                                                    if not http_site_map:
                                                        http_site_map = http_info.get('sitemap')
                                                    if not http_location:
                                                        http_location = http_info.get('location')
                                                    if not http_security_text_hash:
                                                        http_security_text_hash = http_info.get('securitytxt_hash')
                                            except Exception:
                                                logger.exception(f'problem with shodan data raw {shoda_data_raw}')
                                        if not cpe:
                                            cpe = None
                                        device.set_shodan_data(city=shodan_info.get('city'),
                                                               region_code=shodan_info.get('region_code'),
                                                               country_name=shodan_info.get('country_name'),
                                                               org=shodan_info.get('org'),
                                                               os=shodan_info.get('os'),
                                                               cpe=cpe,
                                                               isp=shodan_info.get('isp'),
                                                               ports=shodan_info.get('ports')
                                                               if isinstance(shodan_info.get('ports'), list) else None,
                                                               vulns=vulns,
                                                               http_location=http_location,
                                                               http_server=http_server,
                                                               http_site_map=http_site_map,
                                                               http_security_text_hash=http_security_text_hash)
                                    except Exception:
                                        logger.exception(f'Problem parsing shodan info for {public_ip}')

                        device.add_nic(iface.get('MacAddress'), ec2_ips)

                    if ec2_ips:
                        ec2_id_to_ips[device_id] = ec2_ips

                    specific_private_ip_address = device_raw.get('PrivateIpAddress')
                    if specific_private_ip_address:
                        private_ips_to_ec2[specific_private_ip_address] = device_id
                    device.power_state = POWER_STATE_MAP.get(device_raw.get('State', {}).get('Name'),
                                                             DeviceRunningState.Unknown)
                    try:
                        if POWER_STATE_MAP.get(device_raw.get('State', {}).get('Name'),
                                               DeviceRunningState.Unknown) != DeviceRunningState.TurnedOn:
                            device.last_seen = datetime.datetime.now()
                    except Exception:
                        logger.exception(f'Problem adding last seen')
                    try:
                        device.launch_time = parse_date(device_raw.get('LaunchTime'))
                    except Exception:
                        logger.exception(f'Problem getting launch time for {device_raw}')
                    device.image_id = device_raw.get('ImageId')

                    try:
                        iam_instance_profile_raw = device_raw.get('IamInstanceProfile')
                        if iam_instance_profile_raw:
                            iam_instance_profile_id = iam_instance_profile_raw.get('Id')
                            if iam_instance_profile_id and iam_instance_profile_id in instance_profiles_dict:
                                ec2_instance_attached_role = instance_profiles_dict[iam_instance_profile_id]
                                device.aws_attached_role = AWSRole(
                                    role_name=ec2_instance_attached_role.get('role_name'),
                                    role_arn=ec2_instance_attached_role.get('arn'),
                                    role_id=ec2_instance_attached_role.get('role_id'),
                                    role_description=ec2_instance_attached_role.get('description'),
                                    role_permissions_boundary_policy_name=ec2_instance_attached_role.get(
                                        'permissions_boundary_policy_name'),
                                    role_attached_policies_named=ec2_instance_attached_role.get(
                                        'attached_policies_names')
                                )
                    except Exception:
                        logger.exception(f'Could not parse iam instance profile {iam_instance_profile_raw}')

                    try:
                        # Parse load balancers info
                        associated_lbs = []
                        for ip in ec2_ips:
                            if ip in elb_by_ip:
                                associated_lbs.extend(elb_by_ip[ip])

                        if device_id in elb_by_iid:
                            associated_lbs.extend(elb_by_iid[device_id])

                        for lb_raw in associated_lbs:
                            try:
                                ips = lb_raw.get('ips')
                                lb_scheme = lb_raw.get('scheme')
                                elb_dns = lb_raw.get('dns')
                                device.add_aws_load_balancer(
                                    name=lb_raw.get('name'),
                                    dns=elb_dns,
                                    scheme=lb_scheme,
                                    type=lb_raw.get('type'),
                                    lb_protocol=lb_raw.get('lb_protocol'),
                                    lb_port=lb_raw.get('lb_port'),
                                    instance_protocol=lb_raw.get('instance_protocol'),
                                    instance_port=lb_raw.get('instance_port'),
                                    ips=ips,
                                    last_ip_by_dns_query=lb_raw.get('last_ip_by_dns_query')
                                )
                            except Exception:
                                logger.exception(f'Error parsing lb: {lb_raw}')
                    except Exception:
                        logger.exception(f'Error parsing load balancers information')

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

                                    eks_host_ip = pod_status.get('host_ip')
                                    eks_ec2_instance_id = private_ips_to_ec2.get(eks_host_ip)
                                    device.set_instance_or_node(
                                        container_instance_name=(pod_raw.get('spec') or {}).get('node_name'),
                                        container_instance_id=eks_ec2_instance_id
                                    )

                                    if self.__correlate_eks_ec2 is True:
                                        device.cloud_provider = 'AWS'
                                        device.cloud_id = eks_ec2_instance_id

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
            logger.exception(f'Problem parsing eks data')

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
                                    if self.__correlate_ecs_ec2 is True:
                                        device.cloud_provider = 'AWS'
                                        device.cloud_id = ecs_ec2_instance_id

                                    for attribute in container_instance_raw_data.get('attributes'):
                                        attribute_name = attribute.get('name')
                                        attribute_value = attribute.get('value')

                                        if not isinstance(attribute_name, str) or not isinstance(attribute_value, str):
                                            continue

                                        attribute_name = attribute_name.lower()
                                        if attribute_name == 'ecs.ami-id':
                                            device.image_id = attribute_value

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

                                    # There might be a connected load balancer here
                                    try:
                                        if private_ip and private_ip[0] in elb_by_ip:
                                            for lb_raw in elb_by_ip[private_ip[0]]:
                                                ips = lb_raw.get('ips')
                                                lb_scheme = lb_raw.get('scheme')
                                                elb_dns = lb_raw.get('dns')
                                                device.add_aws_load_balancer(
                                                    name=lb_raw.get('name'),
                                                    dns=elb_dns,
                                                    scheme=lb_scheme,
                                                    type=lb_raw.get('type'),
                                                    lb_protocol=lb_raw.get('lb_protocol'),
                                                    lb_port=lb_raw.get('lb_port'),
                                                    instance_protocol=lb_raw.get('instance_protocol'),
                                                    instance_port=lb_raw.get('instance_port'),
                                                    ips=ips,
                                                    last_ip_by_dns_query=lb_raw.get('last_ip_by_dns_query')
                                                )
                                    except Exception:
                                        logger.exception(f'Error parsing lb for Fargate: {lb_raw}')
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
                            device.vpc_name = vpcs_by_id.get(device_vpc_id)

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
            logger.exception(f'Problem parsing ecs data')

        try:
            if nat_gateways:
                for nat_gateway_raw in nat_gateways:
                    device = self._new_device_adapter()
                    device.id = nat_gateway_raw['NatGatewayId']

                    device.aws_source = aws_source
                    device.aws_region = aws_region
                    device.account_tag = account_tag
                    device.aws_device_type = 'NAT'

                    tags_dict = {i['Key']: i['Value'] for i in nat_gateway_raw.get('Tags', {})}
                    for key, value in tags_dict.items():
                        device.add_aws_ec2_tag(key=key, value=value)
                        device.add_key_value_tag(key, value)

                    vpc_id = nat_gateway_raw.get('VpcId')
                    if vpc_id and isinstance(vpc_id, str):
                        vpc_id = vpc_id.lower()
                        device.vpc_id = vpc_id
                        device.vpc_name = vpcs_by_id.get(vpc_id)

                    subnet_id = nat_gateway_raw.get('SubnetId')
                    if subnet_id:
                        device.subnet_id = subnet_id
                        device.subnet_name = (subnets_by_id.get(subnet_id) or {}).get('name')
                    device.name = tags_dict.get('Name')

                    for nat_gateway_nic in (nat_gateway_raw.get('NatGatewayAddresses') or []):
                        private_ip = nat_gateway_nic.get('PrivateIp')
                        public_ip = nat_gateway_nic.get('PublicIp')
                        ips = []
                        if private_ip:
                            ips.append(private_ip)
                        if public_ip:
                            ips.append(public_ip)
                            device.add_public_ip(public_ip)
                        device.add_nic(ips=ips)

                    device.set_raw(nat_gateway_raw)
                    yield device
        except Exception:
            logger.exception(f'Problem parsing nat gateways')

        # Parse ELB's
        try:
            for elb_raw in all_elbs:
                device = self._new_device_adapter()
                device.id = elb_raw['name']
                device.name = elb_raw['name']
                device.aws_device_type = 'ELB'
                device.aws_source = aws_source
                device.aws_region = aws_region
                device.account_tag = account_tag
                ips = elb_raw.get('ips') or []
                last_ip_by_dns_query = elb_raw.get('last_ip_by_dns_query')
                lb_scheme = elb_raw.get('scheme')
                elb_dns = elb_raw.get('dns')
                subnets = []
                for subnet_id in (elb_raw.get('subnets') or []):
                    subnet_name = (subnets_by_id.get(subnet_id) or {}).get('name')
                    if subnet_name:
                        subnets.append(f'{subnet_id} ({subnet_name})')
                    else:
                        subnets.append(subnet_id)
                device.add_aws_load_balancer(
                    name=elb_raw.get('name'),
                    dns=elb_dns,
                    scheme=lb_scheme,
                    type=elb_raw.get('type'),
                    ips=ips,
                    last_ip_by_dns_query=last_ip_by_dns_query,
                    subnets=subnets
                )
                device.vpc_id = elb_raw.get('vpcid')
                device.vpc_name = vpcs_by_id.get(elb_raw.get('vpcid'))
                if last_ip_by_dns_query:
                    ips.append(last_ip_by_dns_query)

                device.add_nic(ips=ips)

                try:
                    for security_group in (elb_raw.get('security_groups') or []):
                        security_group_raw = security_group_dict.get(security_group)
                        if security_group_raw and isinstance(security_group_raw, dict):
                            outbound_rules = self.__make_ip_rules_list(security_group_raw.get('IpPermissionsEgress'))
                            inbound_rules = self.__make_ip_rules_list(security_group_raw.get('IpPermissions'))
                            device.add_aws_security_group(name=security_group_raw.get('GroupName'),
                                                          outbound=outbound_rules,
                                                          inbound=inbound_rules)

                            try:
                                all_rules_lists = [(outbound_rules, 'EGRESS'), (inbound_rules, 'INGRESS')]
                                for rule_list, direction in all_rules_lists:
                                    self.__add_generic_firewall_rules(
                                        device,
                                        security_group_raw.get('GroupName'),
                                        'AWS ELB Security Group',
                                        direction,
                                        rule_list
                                    )
                            except Exception:
                                logger.exception(f'Could not add generic firewall rules')
                        else:
                            device.add_aws_security_group(name=security_group_raw.get('GroupName'))
                except Exception:
                    logger.exception(f'Problem getting security groups at {device_raw}')
                device.set_raw(elb_raw)
                yield device
        except Exception:
            logger.exception(f'Failure adding ELBs')

    def _parse_raw_data_inner_ssm(
            self,
            device_raw_data_all: Tuple[Dict[str, Dict], Dict[str, Dict], Dict[str, str]],
            aws_source
    ):
        device_raw_data, patch_group_to_patch_baseline_mapping, extra_data = device_raw_data_all
        basic_data = device_raw_data.get('basic_data')
        if not basic_data:
            logger.warning('Wierd device, no basic data!')
            return None

        device = self._new_device_adapter()
        device.id = 'ssm-' + basic_data['InstanceId']
        device.aws_source = aws_source
        device.cloud_provider = 'AWS'
        device.cloud_id = basic_data['InstanceId']
        if extra_data.get('region'):
            device.aws_region = extra_data.get('region')
        if extra_data.get('account_tag'):
            device.account_tag = extra_data.get('account_tag')

        # Parse ssm data
        ssm_data = SSMInfo()
        ssm_data.ping_status = basic_data.get('PingStatus')
        ssm_data.last_ping_date = parse_date(basic_data.get('LastPingDateTime'))
        device.last_seen = parse_date(basic_data.get('LastPingDateTime'))
        ssm_data.agent_version = basic_data.get('AgentVersion')
        try:
            ssm_data.is_latest_version = bool(basic_data.get('IsLatestVersion'))
        except Exception:
            logger.exception(f'Problem parsing if ssm agent is latest version')

        device.figure_os(basic_data.get('PlatformName') + ' ' + basic_data.get('PlatformVersion'))
        ssm_data.activation_id = basic_data.get('ActivationId')
        ssm_data.registration_date = parse_date(basic_data.get('RegistrationDate'))
        resource_type = basic_data.get('ResourceType') or ''
        if 'ec2' in resource_type.lower():
            device.aws_device_type = 'EC2'
        elif 'managed' in resource_type.lower():
            device.aws_device_type = 'Managed'

        hostname = basic_data.get('ComputerName') or ''
        device.hostname = basic_data.get('ComputerName')
        ssm_data.association_status = basic_data.get('AssociationStatus')
        ssm_data.last_association_execution_date = parse_date(
            basic_data.get('LastAssociationExecutionDate'))
        ssm_data.last_successful_association_execution_date = parse_date(
            basic_data.get('LastSuccessfulAssociationExecutionDate'))

        patch_group = (device_raw_data.get('tags') or {}).get('Patch Group')
        ssm_data.patch_group = patch_group

        patch_baseline_info = (patch_group_to_patch_baseline_mapping.get(patch_group) or {})
        patch_baseline_identity = patch_baseline_info.get('BaselineIdentity') or {}
        if patch_baseline_identity:
            ssm_data.baseline_id = patch_baseline_identity.get('BaselineId')
            ssm_data.baseline_name = patch_baseline_identity.get('BaselineName')
            ssm_data.baseline_description = patch_baseline_identity.get('BaselineDescription')

        # Compliance
        compliance_summary = device_raw_data.get('compliance_summary')
        if compliance_summary:
            try:
                for compliance_item_summary in compliance_summary:
                    execution_summary = compliance_item_summary.get('ExecutionSummary') or {}

                    compliant_summary = compliance_item_summary.get('CompliantSummary') or {}
                    compliant_severity_summary = compliant_summary.get('SeveritySummary')

                    non_compliant_summary = compliance_item_summary.get('NonCompliantSummary') or {}
                    non_compliant_severity_summary = non_compliant_summary.get('SeveritySummary')

                    ssm_data.compliance_summaries.append(
                        SSMComplianceSummary(
                            compliance_type=compliance_item_summary.get('ComplianceType'),
                            status=compliance_item_summary.get('Status'),
                            overall_severity=compliance_item_summary.get('OverallSeverity'),
                            last_execution=parse_date(execution_summary.get('ExecutionTime')),
                            compliant_count=compliant_summary.get('CompliantCount'),
                            compliant_critical_count=compliant_severity_summary.get('CriticalCount'),
                            compliant_high_count=compliant_severity_summary.get('HighCount'),
                            compliant_medium_count=compliant_severity_summary.get('MediumCount'),
                            compliant_low_count=compliant_severity_summary.get('LowCount'),
                            compliant_informational_count=compliant_severity_summary.get('InformationalCount'),
                            compliant_unspecified_count=compliant_severity_summary.get('UnspecifiedCount'),
                            non_compliant_count=non_compliant_summary.get('NonCompliantCount'),
                            non_compliant_critical_count=non_compliant_severity_summary.get('CriticalCount'),
                            non_compliant_high_count=non_compliant_severity_summary.get('HighCount'),
                            non_compliant_medium_count=non_compliant_severity_summary.get('MediumCount'),
                            non_compliant_low_count=non_compliant_severity_summary.get('LowCount'),
                            non_compliant_informational_count=non_compliant_severity_summary.get('InformationalCount'),
                            non_compliant_unspecified_count=non_compliant_severity_summary.get('UnspecifiedCount')
                        )
                    )
            except Exception:
                logger.exception(f'Problem parsing compliance summary')

        applications = device_raw_data.get(AwsSSMSchemas.Application.value)
        if isinstance(applications, list):
            for app_data in applications:
                try:
                    device.add_installed_software(
                        architecture=app_data.get('Architecture'),
                        name=app_data.get('Name'),
                        version=app_data.get('Version'),
                        vendor=app_data.get('Publisher'),
                        publisher=app_data.get('Publisher')
                    )
                except Exception:
                    logger.exception(f'Failed to add application {app_data} for host {hostname}')

        network = device_raw_data.get(AwsSSMSchemas.Network.value)
        dns_servers = set()
        dhcp_servers = set()
        if isinstance(network, list):
            for network_interface in network:
                try:
                    ips = []
                    ipv4_raw = network_interface.get('IPV4')
                    ipv6_raw = network_interface.get('IPV6')
                    if ipv4_raw:
                        if isinstance(ipv4_raw, list):
                            ips.extend(ipv4_raw)
                        elif isinstance(ipv4_raw, str):
                            ips.append(ipv4_raw)

                    if ipv6_raw:
                        if isinstance(ipv6_raw, list):
                            ips.extend(ipv6_raw)
                        elif isinstance(ipv6_raw, str):
                            ips.append(ipv6_raw)
                    device.add_nic(
                        mac=network_interface.get('MacAddress'),
                        ips=ips,
                        name=network_interface.get('Name'),
                        gateway=network_interface.get('Gateway')
                    )

                    dns_s = network_interface.get('DNSServer')
                    if isinstance(dns_s, str):
                        dns_servers.add(dns_s)

                    dhcp_s = network_interface.get('DHCPServer')
                    if isinstance(dhcp_s, str):
                        dhcp_servers.add(dhcp_s)
                except Exception:
                    logger.exception(f'Failed to add network interface {network_interface} for host {hostname}')

        if dns_servers:
            device.dns_servers = list(dns_servers)

        if dhcp_servers:
            device.dhcp_servers = list(dhcp_servers)

        services = device_raw_data.get(AwsSSMSchemas.Service.value)
        if isinstance(services, list):
            for service_raw in services:
                try:
                    device.add_service(
                        name=service_raw.get('Name'),
                        display_name=service_raw.get('DisplayName'),
                        status=service_raw.get('Status')
                    )
                except Exception:
                    logger.exception(f'Failed to add service {service_raw} for host {hostname}')

        all_patches = device_raw_data.get('patches')
        if isinstance(all_patches, list):
            for pc_raw in all_patches:
                try:
                    device.add_security_patch(
                        security_patch_id=pc_raw.get('Title') + ' ' + pc_raw.get('KBId'),
                        classification=pc_raw.get('Classification'),
                        severity=pc_raw.get('Severity'),
                        state=pc_raw.get('State'),
                        installed_on=parse_date(pc_raw.get('InstalledTime'))
                    )
                except Exception:
                    logger.exception(f'Failed to add patch compliance {pc_raw} for host {hostname}')

        device.ssm_data = ssm_data
        device.set_raw(device_raw_data)
        return device

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

    def _on_config_update(self, config):
        logger.info(f"Loading AWS config: {config}")
        self.__correlate_ecs_ec2 = config.get('correlate_ecs_ec2') or False
        self.__correlate_eks_ec2 = config.get('correlate_eks_ec2') or False
        self.__fetch_instance_roles = config.get('fetch_instance_roles') or False
        self.__fetch_load_balancers = config.get('fetch_load_balancers') or False
        self.__fetch_ssm = config.get('fetch_ssm') or False
        self.__fetch_nat = config.get('fetch_nat') or False
        self.__parse_elb_ips = config.get('parse_elb_ips') or False
        self.__verbose_auth_notifications = config.get('verbose_auth_notifications') or False
        self.__shodan_key = config.get('shodan_key')

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    'name': 'correlate_ecs_ec2',
                    'title': 'Correlate ECS Containers with their EC2 Instance',
                    'type': 'bool'
                },
                {
                    'name': 'correlate_eks_ec2',
                    'title': 'Correlate EKS Containers with their EC2 Instance',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_instance_roles',
                    'title': 'Fetch information about EC2 attached roles',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_load_balancers',
                    'title': 'Fetch information about ELB (Elastic Load Balancers)',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_ssm',
                    'title': 'Fetch information about SSM (System Manager)',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_nat',
                    'title': 'Fetch information about NAT Gateways',
                    'type': 'bool'
                },
                {
                    'name': 'parse_elb_ips',
                    'title': 'Assign ELB IPs to associated devices',
                    'type': 'bool'
                },
                {
                    'name': 'verbose_auth_notifications',
                    'title': 'Show verbose notifications about connection failures',
                    'type': 'bool'
                },
                {
                    'name': 'shodan_key',
                    'title': 'Shodan API key for more IP info',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            "required": [
                'correlate_ecs_ec2',
                'correlate_eks_ec2',
                'fetch_instance_roles',
                'fetch_load_balancers',
                'fetch_ssm',
                'fetch_nat',
                'parse_elb_ips',
                'verbose_auth_notifications'
            ],
            "pretty_name": "AWS Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'correlate_ecs_ec2': False,
            'correlate_eks_ec2': False,
            'fetch_instance_roles': False,
            'fetch_load_balancers': False,
            'fetch_ssm': False,
            'fetch_nat': False,
            'parse_elb_ips': False,
            'verbose_auth_notifications': False,
            'shodan_key': None
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]
