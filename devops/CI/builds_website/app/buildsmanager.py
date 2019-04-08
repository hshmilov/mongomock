"""Defines the BuildsManager class which handles all connections to the db and amazon.

This project assumes the aws settings & credentials are already configured in the machine, either by using aws cli
(aws configure) or by putting it in "~/.aws.config"
"""
import os
import re
import datetime
from typing import List

import paramiko

from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId
from buildscloud.builds_cloud_manager import BuildsCloudManager

AXONIUS_EXPORTS_SERVER = 'exports.axonius.lan'

KEY_NAME = "Builds-VM-Key"  # The key we use for identification.

HD_SIZE_FOR_INSTANCE_IN_GIB = 100
HD_SIZE_FOR_INSTANCE_IN_GIB_FOR_EXPORT_BASED_INSTANCES = 196
OVA_IMAGE_NAME = "Axonius-operational-export-106"

S3_BUCKET_NAME_FOR_OVA = "axonius-releases"
S3_BUCKET_NAME_FOR_EXPORT_LOGS = "axonius-export-logs"

LOCAL_BUILDS_HOST = 'builds-local.axonius.lan' if 'BUILDS_HOST' not in os.environ else os.environ['BUILDS_HOST']
EXTERNAL_BUILDS_HOST = 'builds.in.axonius.com' if 'BUILDS_HOST' not in os.environ else os.environ['BUILDS_HOST']
DB_ADDR = 'mongo'

NUMBER_OF_TEST_INSTANCES_AVAILABLE = 5


class BuildsManager(object):
    """Handles aws and db connections to provide data about instances, dockers, and VM's."""

    def __init__(self, credentials_file_path: str, bypass_token=None):
        """Initialize the object."""
        self.db = MongoClient(
            DB_ADDR,
            username='axonius',
            password='cqNLLfvQetvFog9y3iqi',
            connect=False
        ).builds
        self.bcm = BuildsCloudManager(credentials_file_path)
        self.bypass_token = bypass_token

        # Not Used
        # self.redis_client = redis.StrictRedis(host=BUILDS_HOST)

    def get_instances(self, cloud=None, instance_id=None, vm_type=None):
        mongo_filter = dict()
        if cloud:
            mongo_filter['cloud'] = cloud

        if instance_id:
            mongo_filter['id'] = instance_id

        if vm_type:
            mongo_filter['vm_type'] = vm_type

        cloud_id_to_db = dict()
        for db_instance in self.db.instances.find(mongo_filter):
            if db_instance.get('id'):
                cloud_id_to_db[db_instance['id']] = db_instance

        all_instances = []
        for cloud_instance in self.bcm.get_instances(cloud=cloud, instance_id=instance_id, vm_type=vm_type):
            all_instances.append(
                {
                    'cloud': cloud_instance,
                    'db': cloud_id_to_db.get(cloud_instance['id']) or {}
                }
            )

        # Sort by time of creation
        all_instances.sort(key=lambda x: datetime.datetime.now() if (x['db'] == {}) else x['db']['date'], reverse=True)
        return all_instances

    def add_instances(
            self, cloud, vm_type, name, instance_type, num, image, key_name, public, code,
            owner, fork, branch
    ) -> List[str]:
        if public is True:
            generic, _ = self.bcm.create_public_instances(
                cloud, vm_type, name, instance_type, num, key_name, image, code
            )
        else:
            generic, _ = self.bcm.create_regular_instances(
                cloud, vm_type, name, instance_type, num, key_name, image, code
            )

        owner_full_name, owner_slack_id = owner
        instance_ids = [instance['id'] for instance in generic]
        for i, instance_id in enumerate(instance_ids):
            self.db.instances.insert_one(
                {
                    'cloud': cloud,
                    'id': instance_id,
                    'vm_type': vm_type,
                    'key_name': key_name,
                    'name': name if num == 1 else f'{name}-{i}',
                    'code': code,
                    'date': datetime.datetime.utcnow(),
                    'owner': owner_full_name,
                    'owner_slack_id': owner_slack_id,
                    'fork': fork,
                    'branch': branch
                }
            )
            self.update_last_user_interaction_time(cloud, instance_id)
        return generic

    def terminate_instance(self, cloud, instance_id):
        """Delete an instance by its id."""
        self.update_last_user_interaction_time(cloud, instance_id)
        self.bcm.terminate_instance(cloud, instance_id)
        self.db.instances.update_one({'cloud': cloud, 'id': instance_id}, {'$set': {'terminated': True, }})
        return True

    def stop_instance(self, cloud, instance_id):
        """Delete an instance by its id."""
        self.update_last_user_interaction_time(cloud, instance_id)
        self.bcm.stop_instance(cloud, instance_id)
        return True

    def start_instance(self, cloud, instance_id):
        """Delete an instance by its id."""
        self.update_last_user_interaction_time(cloud, instance_id)
        self.bcm.start_instance(cloud, instance_id)
        return True

    # Exports
    def get_exports_in_progress(self):
        """Gets all the current exports in progress."""
        export_tasks = self.db.exports.find({'status': 'InProgress'}, projection={'_id': 0})

        return list(export_tasks)[::-1]

    def delete_export(self, version):
        """Deletes an export. """
        def _delete_s3_export():
            exports = self.bcm.aws_s3.s3_client.list_objects(Bucket=S3_BUCKET_NAME_FOR_OVA)['Contents']
            to_delete = []
            for export in exports:
                if version == export['Key'].split('/')[0]:
                    to_delete.append(export)

            for current_deletion in to_delete:
                self.bcm.aws_s3.s3_client.delete_object(Bucket=S3_BUCKET_NAME_FOR_OVA, Key=current_deletion['Key'])

            return to_delete

        def delete_from_storage():
            # subprocess.call(['sudo', 'rm', '-rf', '/mnt/smb_share/Releases/{0}'.format(version)],
            #                stdout=subprocess.PIPE)
            pass

        def delete_from_db():
            self.db.exports.update_one(
                {'version': version},
                {'$set': {
                    'status': 'deleted',
                    'date': datetime.datetime.utcnow()
                }}
            )

        export = self.db.exports.find_one({'version': version})
        ami_id = export['ami_id']
        deleted = _delete_s3_export()

        delete_from_storage()
        delete_from_db()
        self.bcm.aws_compute.deregister_ami(ami_id)

        return len(deleted) > 0

    def get_export_by_version(self, version):
        return self.db.exports.find_one({'version': version})

    def get_exports(self, status=None, limit=0):
        """Return all vm exports we have on our s3 bucket."""
        if status is None:
            exports = self.db.exports.find({'status': {"$nin": ["InProgress", "deleted"]}}, {"_id": 0}) \
                .sort('_id', DESCENDING). \
                limit(limit)
        else:
            exports = self.db.exports.find({'status': {"$in": status}}, {"_id": 0}) \
                .sort('_id', DESCENDING) \
                .limit(limit)

        return list(exports)

    def export_ova(self, version, owner, fork, branch, client_name, comments):
        """Exports an instance by its id."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(AXONIUS_EXPORTS_SERVER, username='ubuntu', password='Password2')
        transport = ssh.get_transport()
        channel = transport.open_session()
        channel.set_environment_variable(name='AWS_POLL_DELAY_SECONDS', value='10')
        channel.set_environment_variable(name='AWS_MAX_ATTEMPTS', value='400')

        # Check if there are any currently running exports
        running_exports = self.get_exports(status=['InProgress'])

        # If none are running delete all the previous exports.
        commands = []
        if len(running_exports) == 0:
            commands.append(
                "rm -f /home/ubuntu/exports/axonius_*.py; "
                "rm -rf /home/ubuntu/exports/output-axonius-*; "
                "rm -f /home/ubuntu/exports/build_*.log; "
                "rm -f /home/ubuntu/exports/axonius_*_git_hash.txt"
            )

        export_id = ObjectId()
        commands.extend([
            "cd /home/ubuntu/exports/",
            "/usr/local/bin/packer build -force -var build_name={0} -var fork={1} -var branch={2} -var image={3} axonius_generate_installer.json >> build_{0}.log 2>&1".format(
                version, fork, branch, OVA_IMAGE_NAME),
            "git_hash=$(cat ./axonius_{0}_git_hash.txt)".format(version),
            "/usr/local/bin/packer build -force -var build_name={0} -var fork={1} -var branch={2} -var image={3} axonius_install_system_and_provision.json >> build_{0}.log 2>&1".format(
                version, fork, branch, OVA_IMAGE_NAME),
            "return_code=$?",
            "/home/ubuntu/.local/bin/aws s3 cp ./build_{0}.log s3://{1}/".format(
                version, S3_BUCKET_NAME_FOR_EXPORT_LOGS),
            "curl -k -v -H \"x-auth-token: {2}\" -F \"status=$return_code\" -F \"git_hash=$git_hash\" https://{1}/api/exports/{0}/status".format(
                version, LOCAL_BUILDS_HOST, self.bypass_token)
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

    @staticmethod
    def get_export_running_log(export_version):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(AXONIUS_EXPORTS_SERVER, username='ubuntu', password='Password2')
        with ssh.open_sftp().open('/home/ubuntu/exports/build_{0}.log'.format(export_version), 'r') as remote_file:
            return {'value': remote_file.read().decode('utf-8')}

    def update_export_status(self, export_id, status, git_hash):
        try:
            log = self.bcm.aws_s3.s3_client.get_object(
                Bucket=S3_BUCKET_NAME_FOR_EXPORT_LOGS,
                Key='build_{0}.log'.format(export_id)
            )['Body'].read().decode('utf-8')
        except Exception as exc:
            log = 'Failed to get log for build_{0}.log from s3. Check s3 for more details.\n'.format(export_id)
            log += str(exc)
        export = self.db.exports.find_one({'version': export_id})
        ami_id_match = re.search('^us-east-2: (.*)$', log, re.MULTILINE)
        ami_id = ami_id_match.group(1) if ami_id_match else ''
        download_link = '<a href="http://{0}.s3-accelerate.amazonaws.com/{1}/{1}/{1}_export.ova">Click here</a>'.format(
            S3_BUCKET_NAME_FOR_OVA,
            export['version']
        )
        self.db.exports.update_one(
            {'version': export_id},
            {
                '$set':
                    {
                        'status': status,
                        'log': log,
                        'download_link': download_link,
                        'ami_id': ami_id,
                        'git_hash': git_hash
                    }
            }
        )

        return export is not None

    # Instances metadata
    def update_last_user_interaction_time(self, cloud, instance_id):
        self.db.instances.update_one(
            {'cloud': cloud, 'id': instance_id},
            {'$set': {'last_user_interaction': datetime.datetime.now()}}
        )

    def set_instance_metadata(self, cloud, instance_id, namespace, metadata):
        self.db.instances.update_one(
            {
                'cloud': cloud,
                'id': instance_id
            },
            {
                '$set':
                    {
                        namespace: metadata
                    }
            }
        )

        return True

    def change_bot_monitoring_status(self, cloud, instance_id, status):
        """ Change the bot monitoring status of this instance"""
        self.db.instances.update_one(
            {'cloud': cloud, 'id': instance_id},
            {'$set': {'bot_monitoring': status}}
        )
        self.update_last_user_interaction_time(cloud, instance_id)
        return status
