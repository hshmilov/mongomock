from typing import List, Dict, Set

import boto3


class AWSComputeManager:
    def __init__(self, credentials: dict):
        super().__init__()
        self.ec2_client = boto3.client('ec2', **credentials)
        self.subnet_id_to_name = dict()
        self.image_id_to_name = dict()
        self.owner_amis = dict()
        self.refreshed_cache = False

        self.refresh_cache()

    @staticmethod
    def get_name_tag(tags: List[dict]):
        for tag in tags:
            if tag['Key'] == 'Name':
                return tag['Value']

        return None

    def refresh_cache(self):
        try:
            for subnet in self.ec2_client.describe_subnets()['Subnets']:
                full_name = subnet['CidrBlock']
                name = self.get_name_tag(subnet['Tags'])
                if name:
                    full_name = f'{name} ({full_name})'

                self.subnet_id_to_name[subnet['SubnetId']] = full_name

            for image_details in self.ec2_client.describe_images(Owners=['self'])['Images']:
                self.image_id_to_name[image_details['ImageId']] = image_details.get('Name') or 'Unknown'

            self.refreshed_cache = True
        except Exception:
            # This happens sometimes due to api limit
            pass

    def refresh_images_names(self, images_ids: Set):
        try:
            for image_details in self.ec2_client.describe_images(ImageIds=list(images_ids))['Images']:
                self.image_id_to_name[image_details['ImageId']] = image_details.get('Name') or 'Unknown'
        except Exception:
            print(f'Could not refresh images names, will try later.')
            pass

    def turn_raw_to_generic(self, raw_instance_data):
        result = {
            'cloud': 'aws',
            'id': raw_instance_data['InstanceId'],
            'type': raw_instance_data.get('InstanceType'),
            'key_name': raw_instance_data.get('KeyName'),
            'private_ip': raw_instance_data.get('PrivateIpAddress'),
            'state': raw_instance_data['State']['Name'],
            'security_groups': [group.get('GroupName', 'Unknown') for group in raw_instance_data['SecurityGroups']],
            'image_id': raw_instance_data.get('ImageId')
        }
        name = self.get_name_tag(raw_instance_data['Tags'])
        if name:
            result['name'] = name

        if raw_instance_data.get('PublicIpAddress'):
            result['public_ip'] = raw_instance_data['PublicIpAddress']

        subnet_name = self.subnet_id_to_name.get(raw_instance_data.get('SubnetId'))
        if subnet_name:
            result['subnet'] = subnet_name

        tags = {tag['Key']: tag['Value'] for tag in raw_instance_data['Tags']}
        if tags:
            result['tags'] = tags

        return result

    def get_instances(self, instance_id: str, vm_type: str):
        if not self.refreshed_cache:
            self.refresh_cache()
        if not vm_type:
            # If we don't have a vm_type we just filter on any
            vm_type = '*'
        images_ids = set()
        instances = []
        for page in self.ec2_client.get_paginator('describe_instances').paginate(
                InstanceIds=[instance_id] if instance_id else [],
                Filters=[{'Name': 'tag:VM-Type', 'Values': [vm_type]}]
        ):
            for reservation in page['Reservations']:
                for instance_details in reservation['Instances']:
                    generic = self.turn_raw_to_generic(instance_details)
                    instances.append(generic)
                    images_ids.add(generic['image_id'])

        self.refresh_images_names(images_ids)
        for instance in instances:
            image = self.image_id_to_name.get(instance['image_id'])
            if image:
                instance['image'] = image

            yield instance

    def create_instance(
            self,
            name: str,
            num: int,
            instance_type: str,
            image_id: str,
            key_name: str,
            subnet_id: str,
            hard_disk_size_in_gb: int,
            tags: Dict[str, str],
            security_groups: List[str],
            is_public: bool,
            user_data: str,
    ):
        node_tags = [
            {'Key': 'Name', 'Value': name},
            {'Key': 'Builds-VM', 'Value': 'true'}
        ]

        for tag_name, tag_value in tags.items():
            node_tags.append({
                'Key': tag_name,
                'Value': tag_value
            })

        tags_specifications = [
            {'ResourceType': resource_type, 'Tags': node_tags}
            for resource_type in ['instance', 'volume']
        ]

        args = {
            'ImageId': image_id,
            'InstanceType': instance_type,
            'MinCount': num,
            'MaxCount': num,
            'SubnetId': subnet_id,
            'TagSpecifications': tags_specifications,
            'UserData': user_data,
            'BlockDeviceMappings': [
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'DeleteOnTermination': True
                    }
                }
            ],
            'DisableApiTermination': True,
            'SecurityGroupIds': security_groups
        }

        if hard_disk_size_in_gb:
            args['BlockDeviceMappings'][0]['Ebs']['VolumeSize'] = hard_disk_size_in_gb

        if key_name:
            args['KeyName'] = key_name

        ec2_instances = self.ec2_client.run_instances(**args)
        raw = list(ec2_instances['Instances'])

        if is_public:
            for instance_raw in raw:
                instance_id = dict(instance_raw)['InstanceId']
                allocation = self.ec2_client.allocate_address(Domain='vpc')
                self.ec2_client.create_tags(
                    Resources=[allocation['AllocationId']],
                    Tags=[
                        {
                            'Key': 'Name',
                            'Value': f'{name}-public-ip'
                        }
                    ]
                )
                waiter = self.ec2_client.get_waiter('instance_running')
                waiter.wait(InstanceIds=[instance_id])
                self.ec2_client.associate_address(AllocationId=allocation['AllocationId'], InstanceId=instance_id)

        generic = [{
            'id': raw_item['InstanceId'],
            'name': name,
            'private_ip': raw_item['PrivateIpAddress']
        } for raw_item in raw]
        return generic, raw

    def start_instance(self, instance_id: str):
        self.ec2_client.start_instances(InstanceIds=[instance_id])

    def stop_instance(self, instance_id: str):
        self.ec2_client.stop_instances(InstanceIds=[instance_id])

    def terminate_instance(self, instance_id: str):
        self.ec2_client.modify_instance_attribute(InstanceId=instance_id, DisableApiTermination={'Value': False})
        instance_details = self.ec2_client.describe_instances(InstanceIds=[instance_id])

        if instance_details['Reservations'][0]['Instances'][0].get('PublicIpAddress'):
            public_ip = instance_details['Reservations'][0]['Instances'][0].get('PublicIpAddress')
            address_data = self.ec2_client.describe_addresses(PublicIps=[public_ip])['Addresses'][0]
            self.ec2_client.disassociate_address(AssociationId=address_data['AssociationId'])
            self.ec2_client.release_address(AllocationId=address_data['AllocationId'])

        self.ec2_client.terminate_instances(InstanceIds=[instance_id])

    def deregister_ami(self, ami_id: str):
        self.ec2_client.deregister_image(ImageId=ami_id)
