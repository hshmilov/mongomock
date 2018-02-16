"""
AWSAdapter.py: An adapter for AWS services.
Currently, allows you to view AWS EC2 instances you possess.
"""

__author__ = "Mark Segal"

from axonius.fields import Field, ListField
from axonius.device import Device
from axonius.adapter_base import AdapterBase, DeviceRunningState
from axonius.smart_json_class import SmartJsonClass
import axonius.adapter_exceptions
import boto3
import re
import botocore.exceptions
from botocore.config import Config

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


class AWSAdapter(AdapterBase):
    class MyDevice(Device):
        power_state = Field(DeviceRunningState, 'Power state')
        aws_tags = ListField(AWSTagKeyValue, "AWS EC2 Tags")
        instance_type = Field(str, "AWS EC2 Instance Type")
        key_name = Field(str, "AWS EC2 Key Name")
        vpc_id = Field(str, "AWS EC2 VPC Id")
        vpc_name = Field(str, "AWS EC2 VPC Name")

        def add_aws_ec2_tag(self, **kwargs):
            self.aws_tags.append(AWSTagKeyValue(**kwargs))

    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)

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
                self.logger.info(f"Setting proxy {client_config[PROXY]}")
                proxies['https'] = client_config[PROXY]

            config = Config(proxies=proxies)
            boto3_client = boto3.client('ec2', **params, config=config)

            # Try to get all the instances. if we have the wrong privileges, it will throw an exception.
            # The only way of knowing if the connection works is to try something. we use DryRun=True,
            # and if it all works then we should get:
            # botocore.exceptions.ClientError: An error occurred (DryRunOperation) when calling the DescribeInstances operation: Request would have succeeded, but DryRun flag is set.
            try:
                boto3_client.describe_instances(DryRun=True)
            except botocore.exceptions.ClientError as e:
                if e.response['Error'].get('Code') != 'DryRunOperation':
                    raise
            return boto3_client
        except botocore.exceptions.BotoCoreError as e:
            message = "Error creating EC2 client for account {0}, reason: {1}".format(
                client_config[AWS_ACCESS_KEY_ID], str(e))
            self.logger.exception(message)
        except botocore.exceptions.ClientError as e:
            message = "Error connecting to client with account {0}, reason: {1}".format(
                client_config[AWS_ACCESS_KEY_ID], str(e))
            self.logger.exception(message)
        raise axonius.adapter_exceptions.ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all EC2 instances from a specific client

        :param str client_name: the name of the client as returned from _get_clients
        :param client_data: The data of the client, as returned from the _parse_clients_data function
        :return: http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.describe_instances
        """
        try:
            amis = set()
            # all devices are returned at once so no progress is logged
            instances = client_data.describe_instances()

            # get all image-ids
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    amis.add(instance['ImageId'])

            try:
                described_images = _describe_images_from_client_by_id(client_data, amis)
            except:
                described_images = {}
                self.logger.exception("Couldn't describe aws images")

            try:
                described_vpcs = _describe_vpcs_from_client(client_data)
            except:
                described_vpcs = {}
                self.logger.exception("Couldn't describe aws vpcs")

            # add image and vpc information to each instance
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance['DescribedImage'] = described_images.get(instance['ImageId'])
                    instance['VPC'] = described_vpcs.get(instance.get('VpcId'))

            return instances
        except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError,
                botocore.exceptions.CredentialRetrievalError, botocore.exceptions.UnknownCredentialError) as e:
            raise axonius.adapter_exceptions.CredentialErrorException(repr(e))
        except botocore.exceptions.BotoCoreError as e:
            raise axonius.adapter_exceptions.AdapterException(repr(e))

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
        for reservation in devices_raw_data.get('Reservations', []):
            for device_raw in reservation.get('Instances', []):
                device = self._new_device()
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
                            device.add_nic(iface.get("MacAddress"), [public_ip], self.logger)
                    device.add_nic(iface.get("MacAddress"), [addr.get('PrivateIpAddress')
                                                             for addr in iface.get("PrivateIpAddresses", [])],
                                   self.logger)
                device.power_state = POWER_STATE_MAP.get(device_raw.get('State', {}).get('Name'),
                                                         DeviceRunningState.Unknown)
                device.set_raw(device_raw)
                yield device

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
