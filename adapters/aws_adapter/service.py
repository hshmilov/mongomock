import logging
logger = logging.getLogger(f'axonius.{__name__}')
import boto3
import botocore.exceptions
from botocore.config import Config
import re

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException, CredentialErrorException, AdapterException
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState, DeviceAdapterContainer
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file

AWS_ACCESS_KEY_ID = 'aws_access_key_id'
REGION_NAME = 'region_name'
AWS_SECRET_ACCESS_KEY = 'aws_secret_access_key'
PROXY = 'proxy'

"""
Matches AWS Instance IDs
"""
aws_ec2_id_matcher = re.compile('i-[0-9a-fA-F]{17}')

# translation table between AWS values to parsed values
POWER_STATE_MAP = {
    'terminated': DeviceRunningState.TurnedOff,
    'stopped': DeviceRunningState.TurnedOff,
    'running': DeviceRunningState.TurnedOn,
    'pending': DeviceRunningState.TurnedOff,
    'shutting-down': DeviceRunningState.ShuttingDown,
    'stopping': DeviceRunningState.ShuttingDown,
}


def _describe_images_from_client_by_id(client, amis):
    """
    Described images (by ids) from a specific client by id

    :param client:
    :param amis list(str): list of image ids to get
    :return dict: image-id -> image
    """

    # the reason I use "Filters->image-id" and not ImageIds is because if I'd use ImageIds
    # would've raise an exception if an image is not found
    # all images are returned at once so no progress is logged
    described_images = client.describe_images(Filters=[{"Name": "image-id", "Values": list(amis)}])

    # make a dictionary from ami key to the value
    return {image['ImageId']: image for image in described_images['Images']}


def _describe_vpcs_from_client(client):
    """
    Described VPCS's from specific client

    :param client: the client (boto3.client('ec2'))
    :return dict: vpc-id -> vpc
    """
    described_images = client.describe_vpcs()

    # make a dictionary from ami key to the value
    return {vpc['VpcId']: vpc for vpc in described_images['Vpcs']}


class AWSTagKeyValue(SmartJsonClass):
    """ A definition for a key value field"""
    key = Field(str, "AWS Tag Key")
    value = Field(str, "AWS Tag Value")


class AwsAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        # EC2-specific fields
        aws_tags = ListField(AWSTagKeyValue, "AWS EC2 Tags")
        instance_type = Field(str, "AWS EC2 Instance Type")
        key_name = Field(str, "AWS EC2 Key Name")
        vpc_id = Field(str, "AWS EC2 VPC Id")
        vpc_name = Field(str, "AWS EC2 VPC Name")
        # ECS-specific fields
        subnet_id = Field(str, "AWS ECS SubnetId")
        cluster_arn = Field(str, "AWS ECS Cluster Arn")
        cluster_name = Field(str, "AWS ECS Cluster Name")
        task_arn = Field(str, "AWS ECS Task Arn")
        task_definition_arn = Field(str, "AWS ECS Task Definition Arn")
        last_status = Field(str, "AWS ECS Task: Last Status")
        desired_status = Field(str, "AWS ECS Task: Desired Status")
        launch_type = Field(str, "AWS ECS Launch Type")
        cpu_units = Field(str, "AWS ECS CPU Units")
        connectivity = Field(str, "AWS ECS Connectivity")
        ecs_group = Field(str, "AWS ECS Group")
        hs_memory = Field(str, "AWS ECS Hard/Soft Memory")
        ecs_platform_version = Field(str, "AWS ECS Platform Version")

        def add_aws_ec2_tag(self, **kwargs):
            self.aws_tags.append(AWSTagKeyValue(**kwargs))

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config[AWS_ACCESS_KEY_ID]

    def _connect_client(self, client_config):
        try:
            params = dict()
            params[REGION_NAME] = client_config[REGION_NAME]
            params[AWS_ACCESS_KEY_ID] = client_config[AWS_ACCESS_KEY_ID]
            params[AWS_SECRET_ACCESS_KEY] = client_config[AWS_SECRET_ACCESS_KEY]

            proxies = dict()
            if PROXY in client_config:
                logger.info(f"Setting proxy {client_config[PROXY]}")
                proxies['https'] = client_config[PROXY]

            config = Config(proxies=proxies)
            try:
                boto3_client_ec2 = boto3.client('ec2', **params, config=config)
            except botocore.exceptions.BotoCoreError as e:
                message = "Could not create EC2 client for account {0}, reason: {1}".format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            except botocore.exceptions.ClientError as e:
                message = "Error connecting to EC2 client with account {0}, reason: {1}".format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            try:
                boto3_client_ecs = boto3.client('ecs', **params, config=config)
            except botocore.exceptions.BotoCoreError as e:
                message = "Could not create ECS client for account {0}, reason: {1}".format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
            except botocore.exceptions.ClientError as e:
                message = "Error connecting to ECS client with account {0}, reason: {1}".format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)

            # Try to get all the instances. if we have the wrong privileges, it will throw an exception.
            # The only way of knowing if the connection works is to try something. we use DryRun=True (for Ec2),
            # and if it all works then we should get:
            # botocore.exceptions.ClientError: An error occurred (DryRunOperation) when calling the DescribeInstances operation: Request would have succeeded, but DryRun flag is set.
            errors = {}
            try:
                boto3_client_ec2.describe_instances(DryRun=True)
            except Exception as e:
                if e.response['Error'].get('Code') != 'DryRunOperation':
                    message = "Error creating EC2 client for account {0}, reason: {1}".format(
                        client_config[AWS_ACCESS_KEY_ID], str(e))
                    logger.warning(message)
                    errors['ec2'] = e
                pass
            try:
                boto3_client_ecs.list_clusters()
            except Exception as e:
                message = "Error creating ECS client for account {0}, reason: {1}".format(
                    client_config[AWS_ACCESS_KEY_ID], str(e))
                logger.warning(message)
                errors['ecs'] = e
                pass
            boto3_clients = {}

            # Tests whether both clients fail the connection test and therefore whether the credentials must be incorrect
            if len(errors) is 2:
                # I save the errors but not sure how to display them.
                raise ClientConnectionException("Could not connect to AWS EC2 or ECS services.")
            else:
                # Stores both EC2 and EKS clients in a dict
                if errors.get('ec2') is None:
                    boto3_clients['ec2'] = boto3_client_ec2
                if errors.get('ecs') is None:
                    boto3_clients['ecs'] = boto3_client_ecs
            return boto3_clients
        except botocore.exceptions.BotoCoreError as e:
            message = "Error creating AWS client for account {0}, reason: {1}".format(
                client_config[AWS_ACCESS_KEY_ID], str(e))
            logger.exception(message)
        except botocore.exceptions.ClientError as e:
            message = "Error connecting to client with account {0}, reason: {1}".format(
                client_config[AWS_ACCESS_KEY_ID], str(e))
            logger.exception(message)
        raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all AWS (EC2 & EKS) instances from a specific client

        :param str client_name: the name of the client as returned from _get_clients
        :param client_data: The data of the client, as returned from the _parse_clients_data function
            if there is EC2 data, client_data['ec2'] will contain that data
            if there is EKS data, client_data['eks'] will contain that data
        :return: http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.describe_instances
        """
        raw_data = {}
        # Checks whether client_data contains EC2 data
        if client_data.get('ec2') is not None:
            try:
                ec2_client_data = client_data.get('ec2')
                amis = set()
                # all devices are returned at once so no progress is logged
                instances = ec2_client_data.describe_instances()

                # get all image-ids
                for reservation in instances['Reservations']:
                    for instance in reservation['Instances']:
                        amis.add(instance['ImageId'])

                try:
                    described_images = _describe_images_from_client_by_id(ec2_client_data, amis)
                except Exception:
                    described_images = {}
                    logger.exception("Couldn't describe aws images")

                try:
                    described_vpcs = _describe_vpcs_from_client(ec2_client_data)
                except Exception:
                    described_vpcs = {}
                    logger.exception("Couldn't describe aws vpcs")

                # add image and vpc information to each instance
                for reservation in instances['Reservations']:
                    for instance in reservation['Instances']:
                        instance['DescribedImage'] = described_images.get(instance['ImageId'])
                        instance['VPC'] = described_vpcs.get(instance.get('VpcId'))

                raw_data['ec2'] = instances
            except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError,
                    botocore.exceptions.CredentialRetrievalError, botocore.exceptions.UnknownCredentialError) as e:
                raise CredentialErrorException(repr(e))
            except botocore.exceptions.BotoCoreError as e:
                raise AdapterException(repr(e))
        # Checks whether client_data contains ECS data
        if client_data.get('ecs') is not None:
            try:
                ecs_client_data = client_data.get('ecs')
                clusters = ecs_client_data.list_clusters()
                clusters = clusters.get('clusterArns')

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
                        logger.exception(f"Couldn't get tasks in cluster {cluster}")

                raw_data['ecs'] = tasks_data
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
            "items": [
                {
                    "name": REGION_NAME,
                    "title": "Region Name",
                    "type": "string"
                },
                {
                    "name": AWS_ACCESS_KEY_ID,
                    "title": "AWS Access Key ID",
                    "type": "string"
                },
                {
                    "name": AWS_SECRET_ACCESS_KEY,
                    "title": "AWS Access Key Secret",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": PROXY,
                    "title": "Proxy",
                    "type": "string"
                }
            ],
            "required": [
                REGION_NAME,
                AWS_ACCESS_KEY_ID,
                AWS_SECRET_ACCESS_KEY
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        # Checks whether devices_raw_data contains EC2 data
        if devices_raw_data.get('ec2') is not None:
            ec2_devices_raw_data = devices_raw_data.get('ec2')
            for reservation in ec2_devices_raw_data.get('Reservations', []):
                for device_raw in reservation.get('Instances', []):
                    device = self._new_device_adapter()
                    tags_dict = {i['Key']: i['Value'] for i in device_raw.get('Tags', {})}
                    for key, value in tags_dict.items():
                        device.add_aws_ec2_tag(key=key, value=value)
                    device.instance_type = device_raw['InstanceType']
                    device.key_name = device_raw['KeyName']
                    if device_raw.get('VpcId') is not None:
                        device.vpc_id = device_raw['VpcId']
                    if device_raw.get("VPC") is not None:
                        vpc_tags_dict = {i['Key']: i['Value'] for i in device_raw['VPC'].get('Tags', {})}
                        if vpc_tags_dict.get('Name') is not None:
                            device.vpc_name = vpc_tags_dict.get('Name')
                    device.name = tags_dict.get('Name', '')
                    device.figure_os(device_raw['DescribedImage'].get('Description', '')
                                     if device_raw['DescribedImage'] is not None
                                     else device_raw.get('Platform'))
                    device.id = device_raw['InstanceId']
                    for iface in device_raw.get('NetworkInterfaces', []):
                        assoc = iface.get("Association")
                        if assoc is not None:
                            public_ip = assoc.get('PublicIp')
                            if public_ip is not None:
                                device.add_nic(iface.get("MacAddress"), [public_ip])
                        device.add_nic(iface.get("MacAddress"), [addr.get('PrivateIpAddress')
                                                                 for addr in iface.get("PrivateIpAddresses", [])])
                    device.power_state = POWER_STATE_MAP.get(device_raw.get('State', {}).get('Name'),
                                                             DeviceRunningState.Unknown)
                    device.set_raw(device_raw)
                    yield device
        # Checks whether devices_raw_data contains ECS data
        if devices_raw_data.get('ecs') is not None:
            ecs_devices_raw_data = devices_raw_data.get('ecs')
            for device_raw in ecs_devices_raw_data:
                try:
                    device = self._new_device_adapter()
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
                        task_arn = device_raw.get('taskArn')
                    except Exception:
                        logger.exception(f'Failed to get cluster data for {device_raw}')
                    if task_arn is not None:
                        device.task_arn = task_arn
                        device.name = task_arn.split('/')[1]
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
                                for network_interface in container.get("networkInterfaces"):
                                    nic = {}
                                    nic['name'] = network_interface.get("attachmentId")
                                    nic['ip'] = network_interface.get("privateIpv4Address")
                                    network_interfaces.append(nic)
                                device.add_container(name=container.get('name'),
                                                     last_status=container.get('lastStatus'), network_interfaces=network_interfaces, containerArn=container.get('containerArn'))
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
            "Linux": "curl http://169.254.169.254/latest/meta-data/instance-id",
            "Windows": 'powershell -Command "& ' +
                       'Invoke-RestMethod -uri http://169.254.169.254/latest/meta-data/instance-id"'
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
        return next(iter(aws_ec2_id_matcher.findall(correlation_cmd_result.strip())), None)

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
