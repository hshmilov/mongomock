"""
AWSAdapter.py: An adapter for AWS services.
Currently, allows you to view AWS EC2 instances you possess.
"""

__author__ = "Mark Segal"

from axonius.adapter_base import AdapterBase, DeviceRunningState
from axonius.parsing_utils import figure_out_os
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
    'terminated': DeviceRunningState.TurnedOff.value,
    'stopped': DeviceRunningState.TurnedOff.value,
    'running': DeviceRunningState.TurnedOn.value,
    'pending': DeviceRunningState.TurnedOff.value,
    'shutting-down': DeviceRunningState.ShuttingDown.value,
    'stopping': DeviceRunningState.ShuttingDown.value,
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
    described_images = client.describe_images(Filters=[{"Name": "image-id", "Values": list(amis)}])

    # make a dictionary from ami key to the value
    return {image['ImageId']: image for image in described_images['Images']}


class AWSAdapter(AdapterBase):
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
            instances = client_data.describe_instances()

            # get all image-ids
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    amis.add(instance['ImageId'])

            described_images = _describe_images_from_client_by_id(client_data, amis)

            # add image information to each instance
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance['DescribedImage'] = described_images.get(instance['ImageId'])

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
            "properties": {
                REGION_NAME: {
                    "type": "string"
                },
                AWS_ACCESS_KEY_ID: {
                    "type": "string"
                },
                AWS_SECRET_ACCESS_KEY: {
                    "type": "password"
                },
                PROXY: {
                    "type": "string"
                }
            },
            "required": [
                REGION_NAME,
                AWS_ACCESS_KEY_ID,
                AWS_SECRET_ACCESS_KEY
            ],
            "type": "object"
        }

    def _parse_raw_data(self, raw_data):
        for reservation in raw_data.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                # TODO: Weiss - This is a bit of a weird dict comprehension.
                state = instance.get('State', {}).get('Name')
                tags_dict = {i['Key']: i['Value']
                             for i in instance.get('Tags', {})}
                yield {
                    "name": tags_dict.get('Name', ''),
                    'OS': figure_out_os(instance['DescribedImage'].get('Description', '')
                                        if instance['DescribedImage'] is not None
                                        else None),
                    'id': instance['InstanceId'],
                    'network_interfaces': self._parse_network_interfaces(instance.get('NetworkInterfaces', [])),
                    'powerState': POWER_STATE_MAP.get(state, DeviceRunningState.Unknown),
                    'raw': instance
                }

    def _parse_network_interfaces(self, interfaces):
        """
        private method to convert AWS's format for a network interface to Axoniuses format
        :param interfaces: list
        :return: list of dict
        """
        network_interfaces = []
        for interface in interfaces:
            assoc = interface.get("Association")
            if assoc is not None:
                public_ip = assoc.get('PublicIp')
                if public_ip is not None:
                    yield {
                        "MAC": interface.get("MacAddress"),
                        "IP": [public_ip]
                    }
            yield {
                "MAC": interface.get("MacAddress"),
                "IP": [addr.get('PrivateIpAddress') for addr in interface.get("PrivateIpAddresses", [])],
            }

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
