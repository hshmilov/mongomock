import argparse
import boto3

from scripts.automate_dev.latest_ami import get_latest_ami


class AmiShare:
    def __init__(self, region='us-east-2'):
        self.region = region

    def get_images(self, region=None):
        ec2_client = self.get_client_for_region(region)
        return ec2_client.describe_images(Owners=['self'])['Images']

    def get_image_names(self, region=None):
        region = region or self.region
        return [image['Name'] for image in self.get_images(region)]

    def set_region(self, region):
        self.region = region

    def get_client_for_region(self, region=None):
        region = region or self.region
        return boto3.client('ec2', region_name=region)

    def get_resource(self, region):
        region = region or self.region
        return boto3.resource('ec2', region_name=region)

    def get_images_by_name(self, name, region=None):
        ec2_client = self.get_client_for_region(region)
        return ec2_client.describe_images(Owners=['self'], Filters=[{'Name': 'name', 'Values': [name]}])['Images']

    def copy_to_region(self, ami_id, dst_region):
        dst_client = self.get_client_for_region(dst_region)

        name = self.get_resource(self.region).Image(ami_id).name

        if name in self.get_image_names(region=dst_region):
            image_details = self.get_images_by_name(name=name, region=dst_region)
            image = image_details[0]
            image_id = image["ImageId"]
            print(f'image {name} is already in {dst_region}: {image_id}')
            return image_id
        else:
            print(f'{name} is missing in {dst_region}, copying')
            res = dst_client.copy_image(
                Name=name,
                Description=name,
                SourceImageId=ami_id,
                SourceRegion=self.region
            )

            return res['ImageId']

    def modify_permissions(self, ami_id, dst_account, region):
        self.wait_for_image(ami_id, region)
        source_ec2 = self.get_resource(region)
        source_ami = source_ec2.Image(ami_id)

        source_snapshot = source_ec2.Snapshot(source_ami.block_device_mappings[0]['Ebs']['SnapshotId'])

        source_snapshot.modify_attribute(
            Attribute='createVolumePermission',
            OperationType='add',
            UserIds=[dst_account]
        )

        source_ami.modify_attribute(Attribute='launchPermission',
                                    ImageId=ami_id,
                                    LaunchPermission={'Add': [{'UserId': dst_account}]})

        shared_with = source_snapshot.describe_attribute(Attribute='createVolumePermission')['CreateVolumePermissions']
        print(f'image {ami_id} is shared with {shared_with} in {region} ({source_ami.name})')

    def wait_for_image(self, ami_id, region=None):
        region = region or self.region
        client = self.get_client_for_region(region)
        waiter = client.get_waiter('image_available')
        print(f'waiting for image {ami_id} in {region}')
        waiter.wait(ImageIds=[ami_id], WaiterConfig={
            'Delay': 60 * 1,
            'MaxAttempts': 60 * 24
        })
        print(f'Image is {ami_id} available in {region}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ami_id', type=str, default='latest')
    parser.add_argument('--src_region', type=str, default='us-east-2')
    parser.add_argument('--dest_region', type=str, required=True)
    parser.add_argument('--dest_account', type=str, required=True)

    args = parser.parse_args()
    print(args)

    image_to_share = args.ami_id

    if image_to_share == 'latest':
        image_to_share = get_latest_ami()

    src_region = args.src_region

    dst_region = args.dest_region
    dst_account_id = args.dest_account

    amishare = AmiShare(region=src_region)
    image_id = amishare.copy_to_region(image_to_share, dst_region)
    amishare.modify_permissions(image_id, dst_account=dst_account_id, region=dst_region)


if __name__ == '__main__':
    main()
