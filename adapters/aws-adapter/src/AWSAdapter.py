"""
AWSAdapter.py: An adapter for AWS services.
Currently, allows you to view AWS EC2 instances you possess.
"""

__author__ = "Mark Segal"

from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os
import boto3
from botocore.exceptions import BotoCoreError


def _describe_images_from_client_by_id(client, amis):
    """
    Described images (by ids) from a specific client by id

    :param client:
    :param amis list(str): list of image ids to get
    :return dict: image-id -> image
    """

    # the reason I use "Filters->image-id" and not ImageIds is because if I'd use ImageIds
    # would've raise an exception if an image is not found
    described_images = client.describe_images(
        Filters=[{"Name": "image-id", "Values": list(amis)}])

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
                aws_id = str(aws_auth['_id'])
                del aws_auth['_id']
                clients_dict[aws_id] = boto3.client('ec2', **aws_auth)
            except BotoCoreError as e:
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

            # for some unexplained reason, if the EC2 instance is associated with a specific account
            # AWS refuses to search the AWS store for the image id, which most of our ImageIDs come from
            described_images_global = _describe_images_from_client_by_id(
                boto3.client('ec2', region_name=client_data._client_config.region_name), amis)

            # in case some images are private, we want to use them
            described_image_local = _describe_images_from_client_by_id(client_data, amis)

            # union dictionary
            described_images = dict(described_images_global, **described_image_local)

            # add image information to each instance
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance['DescribedImage'] = described_images.get(instance['ImageId'])

            return instances
        except BotoCoreError as e:
            self.logger.error("Error fetching EC2 instances for account {0}, reason: {1}", client_name, str(e))
            return "Server Error", 500

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
                    "type": "string"
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
                tags_dict = {i['Key']: i['Value'] for i in instance.get('Tags', {})}
                yield {
                    "name": tags_dict.get('Name', instance['KeyName']),
                    'OS': figure_out_os(instance['DescribedImage']['Description']
                                        if instance['DescribedImage'] is not None
                                        else None),
                    'id': instance['InstanceId'],
                    'network_interfaces': [self._parse_network_interface(interface) for interface in
                                           instance.get('NetworkInterfaces', [])],
                    'raw': instance}

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
