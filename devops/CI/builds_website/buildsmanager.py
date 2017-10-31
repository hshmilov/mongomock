"""Defines the BuildsManager class which handles all connections to the db and amazon.

This project assumes the aws settings & credentials are already configured in the machine, either by using aws cli
(aws configure) or by putting it in "~/.aws.config"
"""
import boto3
import datetime
import json
from pymongo import MongoClient
from bson.objectid import ObjectId

KEY_NAME = "Builds-VM-Key"  # The key we use for identification.
IMAGE_ID = "ami-8f4f60ea"  # Our own imported ubuntu 16.04 Server.
INSTANCE_TYPE = "t2.micro"
SUBNET_ID = "subnet-4154273a"   # Our builds subnet.

S3_EXPORT_PREFIX = "vm-"
S3_BUCKET_NAME_FOR_VM_EXPORTS = "axonius-vms"
S3_ACCELERATED_ENDPOINT = "http://s3-accelerate.amazonaws.com"
S3_EXPORT_URL_TIMEOUT = 3600    # 1 hour to use it before we generate a new one.

DB_HOSTNAME = "builds.axonius.local"

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
        self.db = MongoClient(DB_HOSTNAME).builds  # This just connects to localhost
        self.ec2 = boto3.resource("ec2")  # This assumes we have the credentials already set-up.

        self.ec2_client = boto3.client("ec2");
        self.s3_client = boto3.client("s3")
        self.ecr_client = boto3.client("ecr")

    def postImageDetails(self, repositoryName, imageDigest, forms):
        """
        Posts information about the docker, such as what compiled it.
        :param imageDigest: the image digest starting with a sha256 prefix. for example: sha256:287406e825961dfb756adc28cc315f73aeec26b1de7462b5c17598d8521d017d
        :param forms: a dictionary of all the information we need to store.
        :return: self.getImages.
        """

        self.db.images.update_one({"repositoryName": repositoryName, "imageDigest": imageDigest}, {"$set": forms}, upsert=True)

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
                    "imageTags": image['imageTags']
                    }

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

        return self.getImages()

    def getExportUrl(self, key_name):
        """
        Returns a url to download an s3 object.

        Gets an object name in our s3 bucket,
        and returns a presigned url we can transfer to anyone in order to download this resource.
        """

        s3_accelerated_client = boto3.client("s3", endpoint_url=S3_ACCELERATED_ENDPOINT)
        url = s3_accelerated_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME_FOR_VM_EXPORTS, "Key": key_name},
            ExpiresIn=S3_EXPORT_URL_TIMEOUT)

        return {"url": url, "timeout": S3_EXPORT_URL_TIMEOUT}

    def deleteExport(self, key):
        """Deletes an export. """
        self.s3_client.delete_object(Bucket=S3_BUCKET_NAME_FOR_VM_EXPORTS, Key=key)

        return self.getExports()

    def getExports(self, key=None):
        """Return all vm exports we have on our s3 bucket."""
        try:
            object_list = self.s3_client.list_objects(Bucket=S3_BUCKET_NAME_FOR_VM_EXPORTS,
                                                      Prefix=S3_EXPORT_PREFIX)["Contents"]
        except KeyError:
            return {}

        exports_in_db_list = []
        for i in self.db.exports.find({}):
            i["_id"] = str(i["_id"])
            exports_in_db_list.append(i)


        exports_list = []
        for o in object_list:
            s3 = {"ETag": o["ETag"], "Key": o["Key"], "LastModified": o["LastModified"], "Size": sizeof_fmt(o["Size"])}
            db = {}

            for d in exports_in_db_list:

                if d["bucket_key"] == o["Key"]:
                    db = d
            exports_list.append({"s3": s3, "db": db})

        # Sort by time of creation
        exports_list.sort(key=lambda x: x['db']['date'], reverse=True)

        return exports_list

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
        export_tasks = self.ec2_client.describe_export_tasks()['ExportTasks']
        return export_tasks

    def getInstances(self, ec2_id=None):
        """Return the different aws instances & our internal db."""
        if (ec2_id is None):
            db_instances = self.db.instances.find({})
        else:
            db_instances = self.db.instances.find({"ec2_id": ec2_id})


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
        ec2_instances = list(self.ec2.instances.filter(Filters=[{"Name": "tag:VM-Type", "Values": ["Builds-VM"]}]))

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
            ec2_i["state"] = i.state["Name"]
            ec2_i["vpc_name"] = ""

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

    def addInstance(self, name, owner, comments, configuration_name, configuration_code,
                    image_id=IMAGE_ID, instance_type=INSTANCE_TYPE, 
                    key_name=KEY_NAME, subnet_id=SUBNET_ID):
        """As the name suggests, make a new instance."""

        # Give names to our instance and volume

        name_tag = [
            {"Key": "Name", "Value": "Builds-%s" % (name, )},
            {"Key": "VM-Type", "Value": "Builds-VM"}
            ]

        ts1 = {}
        ts1["ResourceType"] = "instance"
        ts1["Tags"] = name_tag

        ts2 = {}
        ts2["ResourceType"] = "volume"
        ts2["Tags"] = name_tag
        tags_specifications = [ts1, ts2]

        ec2_instances = self.ec2.create_instances(ImageId=image_id, InstanceType=instance_type, KeyName=key_name,
                                                  MinCount=1, MaxCount=1, SubnetId=subnet_id, 
                                                  TagSpecifications=tags_specifications,
                                                  UserData=configuration_code,
                                                  BlockDeviceMappings=[
                                                      {
                                                          'DeviceName': '/dev/sda1',
                                                          'Ebs': {
                                                              'DeleteOnTermination': True
                                                          }
                                                      }
                                                  ]
                                                  )

        instance_id = ec2_instances[0].id

        self.db.instances.insert_one({"name": name,
                                      "owner": owner,
                                      "comments": comments,
                                      "configuration_name": configuration_name,
                                      "configuration_code": configuration_code,
                                      "ec2_id": instance_id,
                                      "date": datetime.datetime.utcnow()})

        return self.getInstances()  # Return new list of vms

    def terminateInstance(self, ec2_id):
        """Delete an instance by its id."""
        self.ec2.instances.filter(InstanceIds=[ec2_id]).terminate()

        # Do not delete instances from the db. just update that they are terminated.
        self.db.instances.update_one({"ec2_id": ec2_id}, {"$set": {"terminated": True}})
        # deleted = self.db.instances.delete_one({"ec2_id": ec2_id})
        return self.getInstances()

    def stopInstance(self, ec2_id):
        """Delete an instance by its id."""
        self.ec2.instances.filter(InstanceIds=[ec2_id]).stop()
        return self.getInstances()

    def startInstance(self, ec2_id):
        """Delete an instance by its id."""
        self.ec2.instances.filter(InstanceIds=[ec2_id]).start()
        return self.getInstances()

    def exportInstance(self, ec2_id, owner, client_name, comments):
        """Exports an instance by its id."""
        instance_db = self.getInstances(ec2_id=ec2_id)[0]

        result = self.ec2_client.create_instance_export_task(
            Description="Export task of instance %s (%s)." % (ec2_id, instance_db['db']['name']),
            InstanceId=ec2_id,
            TargetEnvironment='vmware',
            ExportToS3Task={
                'ContainerFormat': 'ova',
                'DiskImageFormat': 'vmdk',
                'S3Bucket': 'axonius-vms',
                'S3Prefix': 'vm-'
            }
        )

        db_json = dict()
        db_json['name'] = instance_db['db']['name']
        db_json['ec2_id'] = ec2_id
        db_json['owner'] = owner
        db_json['client_name'] = client_name
        db_json['comments'] = comments
        db_json['bucket_key'] = result['ExportTask']['ExportToS3Task']['S3Key']
        db_json['export_result'] = result['ExportTask']
        db_json['date'] = datetime.datetime.utcnow()
        db_json['configuration_name'] = instance_db['db']['configuration_name']
        db_json['configuration_code'] = instance_db['db']['configuration_code']
        db_json['manifest'] = self.getManifest(ec2_id)


        self.db.exports.insert_one(db_json)
        return self.getExportsInProgress()

    def deleteConfiguration(self, object_id):
        self.db.configurations.update_one({"_id": ObjectId(object_id)}, {"$set": {"deleted": True}})
        return self.getConfigurations()

    def getConfigurations(self):
        """Gets all the configurations currently on the system. """

        # Get all configurations that have deleted: false or do not have deleted at all.

        all_configurations = list(self.db.configurations.find(
            {"$or": [{"deleted": { "$exists": False}}, {"deleted": False}]}
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

        return self.getConfigurations()

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
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
