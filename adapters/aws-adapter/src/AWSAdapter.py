"""
AWSAdapter.py: An adapter for AWS services.
Currently, allows you to view AWS EC2 instances you possess.
"""

__author__ = "Mark Segal"

from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os
import axonius.AdapterExceptions
import boto3
import re
import botocore.exceptions

"""
Matches AWS Instance IDs
"""
aws_ec2_id_matcher = re.compile('i-[0-9a-fA-F]{17}')


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

    def _parse_clients_data(self, clients_config):
        clients_dict = {}
        for aws_auth in clients_config:
            try:
                aws_id = aws_auth['aws_access_key_id']
                del aws_auth['_id']
                clients_dict[aws_id] = boto3.client('ec2', **aws_auth)
            except axonius.BotoCoreError as e:
                self.logger.error("Error creating EC2 client for account {0}, reason: {1}", aws_auth.meta.id, str(e))
        return clients_dict

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
            raise axonius.AdapterExceptions.CredentialErrorException(repr(e))
        except botocore.exceptions.BotoCoreError as e:
            raise axonius.AdapterExceptions.AdapterException(repr(e))

    def _clients_schema(self):
        """
        The schema AWSAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "properties": {
                "region_name": {
                    "type": "string"
                },
                "aws_access_key_id": {
                    "type": "string"
                },
                "aws_secret_access_key": {
                    "type": "password"
                }
            },
            "required": [
                "region_name",
                "aws_access_key_id",
                "aws_secret_access_key"
            ],
            "type": "object"
        }

    def _parse_raw_data(self, raw_data):
        for reservation in raw_data['Reservations']:
            for instance in reservation['Instances']:
                tags_dict = {i['Key']: i['Value']
                             for i in instance.get('Tags', {})}
                yield {
                    "name": tags_dict.get('Name', instance['KeyName']),
                    'OS': figure_out_os(instance['DescribedImage']['Description']
                                        if instance['DescribedImage'] is not None
                                        else None),
                    'id': instance['InstanceId'],
                    'network_interfaces': [self._parse_network_interface(interface) for interface in
                                           instance.get('NetworkInterfaces', [])],
                    'raw': instance
                }

    def _parse_network_interface(self, interface):
        """
        private method to convert AWS's format for a network interface to Axoniuses format
        :param interface: dict
        :return: dict
        """
        public_ip = None
        assoc = interface.get("Association")
        if assoc is not None:
            public_ip = assoc.get('PublicIp')

        return {
            "MAC": interface.get("MacAddress"),
            "private_ip": [addr.get('PrivateIpAddress') for addr in interface.get("PrivateIpAddresses", [])],
            "public_ip": [public_ip]
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
        return next(aws_ec2_id_matcher.findall(correlation_cmd_result.strip()), None)
