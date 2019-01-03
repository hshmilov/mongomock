"""Defines the BuildsManager class which handles all connections to the db and amazon.

This project assumes the aws settings & credentials are already configured in the machine, either by using aws cli
(aws configure) or by putting it in "~/.aws.config"
"""
import re
import subprocess
import boto3
import datetime
import json
import paramiko
import awsutils
import redis
import random
from pymongo import MongoClient
from bson.objectid import ObjectId

BUILDS_INSTANCE_VM_TYPE = "Builds-VM"
BUILDS_DEMO_VM_TYPE = "Demo-VM"

AXONIUS_EXPORTS_SERVER = 'exports.axonius.lan'

KEY_NAME = "Builds-VM-Key"  # The key we use for identification.
PRIVATE_SUBNET_ID = "subnet-4154273a"   # Our private builds subnet.
PUBLIC_SUBNET_ID = "subnet-942157ef"   # Our public subnet.
PUBLIC_SECURITY_GROUP = "sg-f5742f9e"
DEFAULT_SECURITY_GROUP = "sg-8e00dce6"

IMAGE_ID = "ami-0cd429efcede712c7"  # Our own imported ubuntu 16.04 Server.
OVA_IMAGE_NAME = "Axonius-operational-export-106"

S3_EXPORT_PREFIX = "vm-"
S3_BUCKET_NAME_FOR_VM_EXPORTS = "axonius-vms"
S3_BUCKET_NAME_FOR_OVA = "axonius-releases"
S3_BUCKET_NAME_FOR_EXPORT_LOGS = "axonius-export-logs"
S3_ACCELERATED_ENDPOINT = "http://s3-accelerate.amazonaws.com"
S3_EXPORT_URL_TIMEOUT = 604700  # a week to use it before we generate a new one.

BUILDS_HOST = 'builds-local.axonius.lan'
EXTERNAL_BUILDS_HOST = 'builds.in.axonius.com'

NUMBER_OF_TEST_INSTANCES_AVAILABLE = 5

NEW_INSTANCE_BOOT_SCRIPT = """#!/bin/bash
set -x
exec 1>/axonius-install.log 2>&1
echo Installing docker.
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce
sudo apt-get install -y python3-pip
sudo apt-get -y upgrade
"""


class BuildsManager(object):
    """Handles aws and db connections to provide data about instances, dockers, and VM's."""

    def __init__(self):
        """Initialize the object."""
        self.db = MongoClient(BUILDS_HOST).builds  # This just connects to localhost
        self.ec2 = boto3.resource("ec2")  # This assumes we have the credentials already set-up.

        self.ec2_client = boto3.client("ec2")
        self.s3_client = boto3.client("s3")
        self.ecr_client = boto3.client("ecr")

        # Not Used
        # self.redis_client = redis.StrictRedis(host=BUILDS_HOST)

    def get_cloud_options(self):
        """
        Returns options provided by our cloud provider about instanaces options.
        :return:
        """

        cloud_options = dict()

        security_groups_dict = dict()
        for security_group_raw_answer in awsutils.get_paginated_next_token_api(
                self.ec2_client.describe_security_groups):
            for security_group in security_group_raw_answer['SecurityGroups']:
                security_groups_dict[security_group['GroupId']] = security_group['GroupName']

        cloud_options['security_groups'] = security_groups_dict

        return cloud_options

    def postImageDetails(self, repositoryName, imageDigest, forms):
        """
        Posts information about the docker, such as what compiled it.
        :param imageDigest: the image digest starting with a sha256 prefix. for example: sha256:287406e825961dfb756adc28cc315f73aeec26b1de7462b5c17598d8521d017d
        :param forms: a dictionary of all the information we need to store.
        :return: self.getImages.
        """

        self.db.images.update_one({"repositoryName": repositoryName, "imageDigest": imageDigest}, {
                                  "$set": forms}, upsert=True)
        return True

    def getImages(self, repository_name=None):
        """
        Gets all docker images.

        It goes to our aws-ecr and gets all repositories, then gets all images from all of them.
        """

        db_list = list(self.db.images.find({}))

        images_list = []
        all_repositories = self.ecr_client.describe_repositories()['repositories']
        for repository in all_repositories:
            all_images = self.ecr_client.describe_images(repositoryName=repository['repositoryName'])['imageDetails']

            for image in all_images:
                ecr = {
                    "repository": repository['repositoryName'],
                    "imageDigest": image['imageDigest'],
                    "imagePushedAt": image['imagePushedAt'],
                    "size": sizeof_fmt(image['imageSizeInBytes']),
                }

                try:
                    ecr["imageTags"] = image['imageTags']
                except KeyError:
                    # sometimes its empty.
                    ecr["imageTags"] = []

                db = {}
                for d in db_list:
                    if d['imageDigest'] == image['imageDigest']:
                        db = d
                        db["_id"] = str(db["_id"])
                        break

                images_list.append({"ecr": ecr, "db": db})

        # Sort by time of creation
        images_list.sort(key=lambda x: x['ecr']['imagePushedAt'], reverse=True)

        # Convert all dates to strings
        for i in images_list:
            i['ecr']['imagePushedAt'] = str(i['ecr']['imagePushedAt'])

        return images_list

    def deleteImage(self, repository_name=None, image_digest=None):
        # If we have an id, get the repo name and the digest by yourself.
        self.ecr_client.batch_delete_image(repositoryName=repository_name, imageIds=[{'imageDigest': image_digest}])

        return True

    def getExportUrl(self, key_name):
        """
        Returns a url to download an s3 object.

        Gets an object name in our s3 bucket,
        and returns a presigned url we can transfer to anyone in order to download this resource.
        """

        s3_accelerated_client = boto3.client("s3", endpoint_url=S3_ACCELERATED_ENDPOINT)
        url = s3_accelerated_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME_FOR_OVA, "Key": key_name},
            ExpiresIn=S3_EXPORT_URL_TIMEOUT)

        return {"url": url, "timeout": S3_EXPORT_URL_TIMEOUT}

    def deleteExport(self, version):
        """Deletes an export. """
        def _delete_s3_export():
            exports = self.s3_client.list_objects(Bucket=S3_BUCKET_NAME_FOR_OVA)['Contents']
            to_delete = []
            for export in exports:
                if version == export['Key'].split('/')[0]:
                    to_delete.append(export)

            for current_deletion in to_delete:
                self.s3_client.delete_object(Bucket=S3_BUCKET_NAME_FOR_OVA, Key=current_deletion['Key'])

            return to_delete

        def delete_from_storage():
            subprocess.call(['sudo', 'rm', '-rf', '/mnt/smb_share/Releases/{0}'.format(version)],
                            stdout=subprocess.PIPE)

        def delete_from_db():
            self.db.exports.update_one(
                {"version": version},
                {"$set": {
                    "status": "deleted",
                    "date": datetime.datetime.utcnow()
                }}
            )

        def delete_ami():
            for image in self.ec2.images.filter(Owners=['self']):
                if 'Axonius {0}'.format(version) in image.name:
                    image.deregister()
                    break

        deleted = _delete_s3_export()

        delete_from_storage()

        delete_from_db()

        delete_ami()

        return len(deleted) > 0

    def getExports(self, status=None):
        """Return all vm exports we have on our s3 bucket."""
        if status is None:
            exports = self.db.exports.find({'status': {"$nin": ["InProgress", "deleted"]}}, {"_id": 0})
        else:
            exports = self.db.exports.find({'status': {"$in": status}}, {"_id": 0})

        return list(exports)[::-1]

    def getExportManifest(self, key):
        """ Returns the stored manifest of a specific key. """
        manifest = []
        db = list(self.db.exports.find({"bucket_key": key}))
        if (len(db) > 0):
            i = db[0]
            manifest = i['manifest']

        return manifest

    def getExportsInProgress(self):
        """Gets all the current exports in progress."""
        export_tasks = self.db.exports.find({'status': 'InProgress'}, projection={"_id": 0})

        return list(export_tasks)[::-1]

    def update_last_user_interaction_time(self, ec2_id):
        self.db.instances.update_one({"ec2_id": ec2_id}, {"$set": {"last_user_interaction": datetime.datetime.now()}})

    def getInstances(self, ec2_id=None, vm_type=BUILDS_INSTANCE_VM_TYPE):
        """Return the different aws instances & our internal db."""
        if ec2_id is None:
            db_instances = self.db.instances.find({"vm_type": vm_type})
        else:
            db_instances = self.db.instances.find({"ec2_id": ec2_id, "vm_type": vm_type})

        # Get a list of all subnets and vpc's so we can query much faster
        subnets = list(self.ec2.subnets.all())
        vpcs = list(self.ec2.vpcs.all())

        # Get instance status. The only way to do this is with describe_instance_status
        instance_statuses = self.ec2_client.describe_instance_status()['InstanceStatuses']

        instances_array = []
        for i in db_instances:
            i["_id"] = str(i["_id"])
            instances_array.append(i)

        # Lets get information about our instances.
        ec2_instances = list(self.ec2.instances.filter(Filters=[{"Name": "tag:VM-Type", "Values": [vm_type]}]))

        # After we have this information, we need to build our joined array of information
        all_instances = []
        for i in ec2_instances:
            if (ec2_id is not None and i.id != ec2_id):
                continue
            ec2_i = {}
            ec2_i["id"] = i.id
            try:
                ec2_i["image_description"] = i.image.description
            except AttributeError:
                ec2_i["image_description"] = "Unknown"
            ec2_i["instance_type"] = i.instance_type
            ec2_i["key_name"] = i.key_name
            ec2_i["private_ip_address"] = i.private_ip_address
            ec2_i["public_ip_address"] = i.public_ip_address or ''
            ec2_i["state"] = i.state["Name"]
            ec2_i["vpc_name"] = ""
            ec2_i['security_groups'] = [sec_group.get('GroupName', 'Unknown') for sec_group in i.security_groups]

            # search for the instance status
            for status in instance_statuses:
                if status["InstanceId"] == i.id:
                    ec2_i["instance_status"] = status["InstanceStatus"]["Status"]
                    ec2_i["system_status"] = status["SystemStatus"]["Status"]
                    break

            if i.vpc is not None:
                c_vpc = vpcs[vpcs.index(i.vpc)]   # a local copy we already have
                for tag in c_vpc.tags:
                    if tag["Key"] == "Name":
                        ec2_i["vpc_name"] = tag["Value"]

            if i.subnet is not None:
                c_subnet = subnets[subnets.index(i.subnet)]   # a local copy we already have
                for tag in c_subnet.tags:
                    if tag["Key"] == "Name":
                        ec2_i['subnet'] = "%s (%s)" % (tag["Value"], c_subnet.cidr_block)

            db_i = {}
            for j in instances_array:
                if j["ec2_id"] == i.id:
                    db_i = j
                    #db_i["date"] = str(db_i["date"])
                    break

            all_instances.append({"ec2": ec2_i, "db": db_i})

        # Sort by time of creation
        all_instances.sort(key=lambda x: datetime.datetime.now() if (x['db'] == {}) else x['db']['date'], reverse=True)

        # Convert all dates to strings
        for i in all_instances:
            if i['db'] != {}:
                i['db']['date'] = str(i['db']['date'])

        return all_instances

    def getTestInstance(self):
        """
        Gets a new already-made test instance, creates a new one immediately.
        """
        raise NotImplementedError('Unused')

        # The fllowing code is commented out because in this version of builds we are not using auto-created vm's,
        # but there is a high probability we will use this in the future.

        # while self.redis_client.llen('test_instances') < (NUMBER_OF_TEST_INSTANCES_AVAILABLE + 1):
        #     instance_id = self.add_instance(
        #         'AutoTest_{0}'.format(random.randint(1, 10000)),
        #         'Builds-System',
        #         'Created automatically for automatic tests',
        #         'AutoTests',
        #         "#!/bin/bash\n"
        #         "set -x\n"
        #         "exec 1>/install.log 2>&1\n"
        #         "echo ubuntu:12345678 | chpasswd\n"
        #         "sed -i.bak 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config\n"
        #         # surpress 'sudo: unable to resolve host'
        #         "sed -i.bak 's/127\.0\.1\.1.*/127.0.1.1\t'`hostname`'/' /etc/hosts\n"
        #         "service ssh restart\n"
        #     )['instance_id']
        #
        #     self.redis_client.lpush('test_instances', instance_id)
        #
        # instance_id = self.redis_client.rpop('test_instances').decode('utf-8')
        #
        # return {"instance_id": instance_id}

    def add_instance(self, name, owner, ec2_type, configuration_code, fork, branch,
                     public=False, image_id=IMAGE_ID, key_name=KEY_NAME, subnet_id=PRIVATE_SUBNET_ID,
                     vm_type=BUILDS_INSTANCE_VM_TYPE, security_group_id=DEFAULT_SECURITY_GROUP):
        """As the name suggests, make a new instance."""

        # Give names to our instance and volume
        name_tag = [
            {"Key": "Name", "Value": "{0}-{1}".format(vm_type, name)},
            {"Key": "VM-Type", "Value": vm_type}
        ]

        ts1 = {}
        ts1["ResourceType"] = "instance"
        ts1["Tags"] = name_tag

        ts2 = {}
        ts2["ResourceType"] = "volume"
        ts2["Tags"] = name_tag
        tags_specifications = [ts1, ts2]

        subnet_id = subnet_id if not public else PUBLIC_SUBNET_ID
        security_group_id = PUBLIC_SECURITY_GROUP if public else security_group_id
        termination_protection = False if vm_type == BUILDS_INSTANCE_VM_TYPE else True

        args = {
            "ImageId": image_id, "InstanceType": ec2_type, "KeyName": key_name,
            "MinCount": 1, "MaxCount": 1, "SubnetId": subnet_id,
            "TagSpecifications": tags_specifications,
            "UserData": configuration_code,
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "DeleteOnTermination": True
                    }
                }
            ],
            "DisableApiTermination": termination_protection
        }

        args["SecurityGroupIds"] = [security_group_id]

        ec2_instances = self.ec2.create_instances(**args)

        instance_id = ec2_instances[0].id
        elastic_ip_id = ''
        if public:
            allocation = self.ec2_client.allocate_address(Domain='vpc')
            waiter = self.ec2_client.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            self.ec2_client.associate_address(AllocationId=allocation['AllocationId'], InstanceId=instance_id)
            elastic_ip_id = allocation['AllocationId']

        owner_full_name, owner_slack_id = owner

        self.db.instances.insert_one({"name": name,
                                      "owner": owner_full_name,
                                      "owner_slack_id": owner_slack_id,
                                      "configuration_name": "Constant",
                                      "configuration_code": configuration_code,
                                      "ec2_id": instance_id,
                                      "elastic_ip_id": elastic_ip_id,
                                      "date": datetime.datetime.utcnow(),
                                      "vm_type": vm_type,
                                      "fork": fork,
                                      "branch": branch})

        self.update_last_user_interaction_time(instance_id)
        return {"instance_id": instance_id}  # Return new list of vms

    def changeBotMonitoringStatus(self, ec2_id, status):
        """ Change the bot monitoring status of this instance"""
        self.db.instances.update_one({"ec2_id": ec2_id}, {"$set": {"bot_monitoring": status}})
        self.update_last_user_interaction_time(ec2_id)
        return status

    def set_instance_metadata(self, ec2_id, namespace, metadata):
        self.db.instances.update_one(
            {
                "ec2_id": ec2_id
            },
            {
                "$set":
                    {
                        namespace: metadata
                    }
            }
        )

        return True

    def terminateInstance(self, ec2_id):
        """Delete an instance by its id."""
        # If that's a test vm then remove it from the list
        # Unused
        # self.redis_client.lrem('test_instances', 0, ec2_id)

        self.ec2_client.modify_instance_attribute(InstanceId=ec2_id, DisableApiTermination={'Value': False})

        self.ec2.instances.filter(InstanceIds=[ec2_id]).terminate()

        # Do not delete instances from the db. just update that they are terminated.
        instance = self.db.instances.find_one({"ec2_id": ec2_id})
        self.db.instances.update_one({"_id": instance['_id']}, {"$set": {"terminated": True, }})

        elastic_ip_address_id = instance.get('elastic_ip_id', '')
        if elastic_ip_address_id != '':
            waiter = self.ec2_client.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=[instance['ec2_id']])
            self.ec2_client.release_address(AllocationId=elastic_ip_address_id)
        # deleted = self.db.instances.delete_one({"ec2_id": ec2_id})
        self.update_last_user_interaction_time(ec2_id)
        return True

    def stopInstance(self, ec2_id):
        """Delete an instance by its id."""
        self.ec2.instances.filter(InstanceIds=[ec2_id]).stop()
        self.update_last_user_interaction_time(ec2_id)
        return True

    def startInstance(self, ec2_id):
        """Delete an instance by its id."""
        self.ec2.instances.filter(InstanceIds=[ec2_id]).start()
        self.update_last_user_interaction_time(ec2_id)
        return True

    def export_ova(self, version, owner, fork, branch, client_name, comments):
        """Exports an instance by its id."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(AXONIUS_EXPORTS_SERVER, username='ubuntu', password='Password2')
        transport = ssh.get_transport()
        channel = transport.open_session()

        # Check if there are any currently running exports
        running_exports = self.getExports(status=["InProgress"])

        # If none are running delete all the previous exports.
        commands = []
        if len(running_exports) == 0:
            commands.append(
                "rm -f /home/ubuntu/exports/*.py; rm -rf /home/ubuntu/exports/output-axonius-*")

        export_id = ObjectId()
        commands.extend([
            "cd /home/ubuntu/exports/",
            "/usr/local/bin/packer build -force -var build_name={0} -var fork={1} -var branch={2} -var image={3} axonius_generate_installer.json >> build_{0}.log 2>&1".format(
                version, fork, branch, OVA_IMAGE_NAME),
            "/usr/local/bin/packer build -force -var build_name={0} -var fork={1} -var branch={2} -var image={3} axonius_install_system_and_provision.json >> build_{0}.log 2>&1".format(
                version, fork, branch, OVA_IMAGE_NAME),
            "/home/ubuntu/.local/bin/aws s3 cp ./build_{0}.log s3://{1}/".format(
                version, S3_BUCKET_NAME_FOR_EXPORT_LOGS),
            "curl -k -v -F \"status=$?\" https://{1}/exports/{0}/status".format(
                version, BUILDS_HOST)
        ])

        commands = ' ; '.join(commands)

        # Deletes the build log after upload to s3 but only if the upload was successful (&&).
        commands += " && rm -f ./build_{0}.log".format(version)
        channel.exec_command(commands)

        owner_full_name, owner_slack_id = owner

        db_json = dict()
        db_json['_id'] = export_id
        db_json['version'] = version
        db_json['owner'] = owner_full_name
        db_json['owner_slack_id'] = owner_slack_id
        db_json['fork'] = fork
        db_json['branch'] = branch
        db_json['client_name'] = client_name
        db_json['comments'] = comments
        db_json['status'] = 'InProgress'
        # db_json['export_result'] = result['ExportTask']
        db_json['date'] = datetime.datetime.utcnow()

        self.db.exports.insert_one(db_json)
        return True

    def get_export_running_log(self, export_version):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(AXONIUS_EXPORTS_SERVER, username='ubuntu', password='Password2')
        with ssh.open_sftp().open('/home/ubuntu/exports/build_{0}.log'.format(export_version), 'r') as remote_file:
            return {'value': remote_file.read().decode('utf-8')}

    def update_export_status(self, export_id, status):
        try:
            log = self.s3_client.get_object(Bucket=S3_BUCKET_NAME_FOR_EXPORT_LOGS, Key='build_{0}.log'.format(export_id))[
                'Body'].read().decode('utf-8')
        except Exception as exc:
            log = 'Failed to get log for build_{0}.log from s3. Check s3 for more details.\n'.format(export_id)
            log += str(exc)
        export = self.db.exports.find_one({"version": export_id})
        ami_id_match = re.search("^us-east-2: (.*)$", log, re.MULTILINE)
        ami_id = ami_id_match.group(1) if ami_id_match else ''
        self.db.exports.update_one({"version": export_id}, {"$set": {"status": status, "log": log,
                                                                     "download_link": "<a href='http://{0}.s3-accelerate.amazonaws.com/{1}/{1}/{1}_export.ova'>Click here</a>".format(
                                                                         S3_BUCKET_NAME_FOR_OVA,
                                                                         export['version']),
                                                                     "ami_id": ami_id}})
        return export is not None

    def deleteConfiguration(self, object_id):
        self.db.configurations.update_one({"_id": ObjectId(object_id)}, {"$set": {"deleted": True}})
        return True

    def getConfigurations(self):
        """Gets all the configurations currently on the system. """

        # Get all configurations that have deleted: false or do not have deleted at all.

        all_configurations = list(self.db.configurations.find(
            {"$or": [{"deleted": {"$exists": False}}, {"deleted": False}]}
        ))

        # _id is not json serializable...
        for i in all_configurations:
            i["_id"] = str(i["_id"])

        return all_configurations

    def updateConfiguration(self, object_id, name, author, purpose, code):
        """
        Adds new configuration.
        :param object_id: if not None, tries to update the configuration.
        :param name: the name of the configuration
        :param author: who created the configuration
        :param purpose: the purpose of the configuration. for example, its for all dev branches.
        :param code: the actual code that needs to be run on the axonius system
        :return:
        """

        new_configuration = {"name": name, "author": author, "purpose": purpose, "code": code,
                             "date": datetime.datetime.utcnow()}

        if object_id is not None:
            self.db.configurations.update_one({"_id": ObjectId(object_id)}, {"$set": new_configuration})
        else:
            self.db.configurations.insert_one(new_configuration)

        return True

    def getManifest(self, ec2_id, key=None):
        """
        Gets a
        :return: list of dictionaries, each dict has a "key" and "value" vars.
        """

        manifest = []

        if key is not None:
            m = list(self.db.manifests.find({"ec2_id": ec2_id, "key": key}))
            if len(m) > 0:
                manifest.append({"key": m[0]['key'], "value": m[0]['value']})

            return manifest
        manifest_components = self.db.manifests.find({"ec2_id": ec2_id})

        for m in manifest_components:
            m['_id'] = str(m['_id'])
            manifest.append({'key': m['key'], 'value': m['value']})

        # Append the things we already have in our db.
        instance = self.getInstances(ec2_id)
        if len(instance) > 0:
            manifest.append({'key': 'instance', 'value': instance[0]})

        images = self.getImages()
        manifest.append({'key': 'images', 'value': images})

        return manifest

    def postManifest(self, ec2_id, key, value):
        """
        post a new manifest component.

        :param ec2_id: the ec2 id of the instance that the manifest component describes.
        :param key: the key of the key-value combination. for example, "installation-log"
        :param value: the value of the key-value combination. for example, the log of the installation.
        :return: True.
        """

        # try to convert the string to a dict, if possible.
        try:
            value = json.loads(value)
        except json.decoder.JSONDecodeError:
            pass

        self.db.manifests.update_one(
            {"ec2_id": ec2_id, "key": key},
            {"$set": {
                "value": value,
                "date": datetime.datetime.utcnow()
            }},
            upsert=True
        )

        return True


def sizeof_fmt(num, suffix='B'):
    """Some internet function to get number of bytes and return a human readable version of it."""
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
