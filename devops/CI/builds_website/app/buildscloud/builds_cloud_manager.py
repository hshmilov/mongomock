"""
An interface for interacting with the cloud.
This includes many of the options we need generically, but it masks the
"""
import json

from typing import Dict

from buildscloud.builds_cloud_consts import *
from buildscloud.builds_cloud_enums import BuildsComputeType, BuildsStorageType, BuildsDNSType
from buildscloud.compute.aws_compute_manager import AWSComputeManager
from buildscloud.compute.gcp_compute_manager import GCPComputeManager
from buildscloud.dns.cloudflare_dns_manager import CloudFlareDNSManager
from buildscloud.storage.aws_storage_manager import AWSStorageManager
from buildscloud.storage.gcp_storage_manager import GCPStorageManager


class BuildsCloudManager:
    def __init__(
            self,
            credentials_file_path: str
    ):
        self.__compute: Dict = dict()
        self.__storage: Dict = dict()
        self.__dns: Dict = dict()

        self.__parse_credentials_file(credentials_file_path)

    def __parse_credentials_file(self, credentials_file_path: str):
        with open(credentials_file_path, 'rt') as f:
            credentials_file_contents = json.loads(f.read())

        for service_name, service_dict in credentials_file_contents.items():
            service_types = service_dict['types']
            service_data = service_dict['data']
            service_name = service_name.lower()
            for service_type in service_types:
                if service_type == 'compute':
                    self.__compute[service_name] = \
                        BuildsComputeType[service_name.upper()].value(service_data)

                elif service_type == 'storage':
                    self.__storage[service_name] = \
                        BuildsStorageType[service_name.upper()].value(service_data)

                elif service_type == 'dns':
                    self.__dns[service_name] = \
                        BuildsDNSType[service_name.upper()].value(service_data)

    @property
    def aws_compute(self) -> AWSComputeManager:
        return self.__compute['aws']

    @property
    def aws_s3(self) -> AWSStorageManager:
        return self.__storage['aws']

    @property
    def gcp_compute(self) -> GCPComputeManager:
        return self.__compute['gcp']

    @property
    def gcp_storage(self) -> GCPStorageManager:
        return self.__storage['gcp']

    @property
    def cloudflare(self) -> CloudFlareDNSManager:
        return self.__dns['cloudflare']

    def get_instances(
            self,
            cloud: str=None,
            instance_id: str=None,
            vm_type: str=None,
    ):
        cloud_types = [cloud] if cloud else [ct.name.lower() for ct in BuildsComputeType]
        for cloud_type in cloud_types:
            if cloud_type == 'aws':
                yield from self.aws_compute.get_instances(instance_id=instance_id, vm_type=vm_type)
            elif cloud_type == 'gcp':
                yield from self.gcp_compute.get_nodes(node_id=instance_id, vm_type=vm_type)
            else:
                raise ValueError(f'Unsupported compute cloud type {cloud_type}')

    def create_regular_instances(
            self,
            cloud: str,
            vm_type: str,
            name: str,
            instance_type: str,
            num: int,
            key_name: str,
            image: str = None,
            code: str = None,
    ):
        if cloud == 'aws':
            if not image:
                image = AWS_UBUNTU_VANILLA_IMAGE_ID
            generic, raw = self.aws_compute.create_instance(
                f'{vm_type}-{name}',
                num,
                instance_type,
                image,
                key_name,
                AWS_REGULAR_INSTANCE_SUBNET_ID,
                AWS_REGULAR_INSTANCE_DEFAULT_HD_SIZE,
                {'VM-Type': vm_type},
                AWS_REGULAR_INSTANCE_SECURITY_GROUPS,
                False,
                code if code else ''
            )
        elif cloud == 'gcp':
            if not image:
                image = GCP_UBUNTU_VANILLA_IMAGE_ID
            generic, raw = self.gcp_compute.create_node(
                f'{vm_type}-{name}',
                num,
                instance_type,
                image,
                key_name,
                GCP_REGULAR_INSTANCE_NETWORK_ID,
                GCP_REGULAR_INSTANCE_SUBNETWORK_ID,
                GCP_REGULAR_INSTANCE_DEFAULT_HD_SIZE,
                {'vm-type': vm_type.lower()},
                False,
                code
            )
        else:
            raise ValueError(f'Unsupported compute cloud type {cloud}')

        return generic, raw

    def create_public_instances(
            self,
            cloud: str,
            vm_type: str,
            domain: str,
            instance_type: str,
            num: int,
            key_name: str,
            image: str = None,
            code: str = None,
    ):
        if cloud == 'aws':
            if not image:
                image = AWS_UBUNTU_VANILLA_IMAGE_ID
            generic, raw = self.aws_compute.create_instance(
                f'{vm_type.lower()}-{domain}',
                num,
                instance_type,
                image,
                key_name,
                AWS_PUBLIC_INSTANCE_SUBNET_ID,
                AWS_PUBLIC_INSTANCE_DEFAULT_HD_SIZE,
                {'VM-Type': vm_type},
                AWS_PUBLIC_INSTANCE_SECURITY_GROUPS,
                True,
                code if code else ''
            )
        elif cloud == 'gcp':
            if not image:
                image = GCP_UBUNTU_VANILLA_IMAGE_ID
            generic, raw = self.gcp_compute.create_node(
                f'{vm_type}-{domain}',
                num,
                instance_type,
                image,
                CLOUD_KEYS[key_name],
                GCP_PUBLIC_INSTANCE_NETWORK_ID,
                GCP_PUBLIC_INSTANCE_SUBNETWORK_ID,
                GCP_PUBLIC_INSTANCE_DEFAULT_HD_SIZE,
                {'vm-type': vm_type.lower()},
                True,
                code
            )
        else:
            raise ValueError(f'Unsupported compute cloud type {cloud}')

        return generic, raw

    def stop_instance(self, cloud: str, instance_id: str):
        if cloud == 'aws':
            self.aws_compute.stop_instance(instance_id)
        elif cloud == 'gcp':
            self.gcp_compute.stop_node(instance_id)
        else:
            raise ValueError(f'Unsupported compute cloud type {cloud}')

    def terminate_instance(self, cloud: str, instance_id: str):
        if cloud == 'aws':
            self.aws_compute.terminate_instance(instance_id)
        elif cloud == 'gcp':
            self.gcp_compute.terminate_node(instance_id)
        else:
            raise ValueError(f'Unsupported compute cloud type {cloud}')

    def start_instance(self, cloud: str, instance_id: str):
        if cloud == 'aws':
            self.aws_compute.start_instance(instance_id)
        elif cloud == 'gcp':
            self.gcp_compute.start_node(instance_id)
        else:
            raise ValueError(f'Unsupported compute cloud type {cloud}')
