"""Defines the BuildsManager class which handles all connections to the db and amazon.

This project assumes the aws settings & credentials are already configured in the machine, either by using aws cli
(aws configure) or by putting it in "~/.aws.config"
"""
import re
import datetime
import time
import json
from typing import List

import paramiko

from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId

from buildscloud.builds_cloud_consts import NO_INTERNET_NETWORK_SECURITY_OPTION
from buildscloud.builds_cloud_manager import BuildsCloudManager
from config import TOKENS_PATH, CREDENTIALS_PATH, LOCAL_BUILDS_HOST
from slacknotifier import SlackNotifier

AXONIUS_EXPORTS_SERVER = 'exports.axonius.lan'

KEY_NAME = "Builds-VM-Key"  # The key we use for identification.

HD_SIZE_FOR_INSTANCE_IN_GIB = 100
HD_SIZE_FOR_INSTANCE_IN_GIB_FOR_EXPORT_BASED_INSTANCES = 196
OVA_IMAGE_NAME = "Axonius-operational-export-106"

S3_BUCKET_NAME_FOR_OVA = "axonius-releases"
S3_BUCKET_NAME_FOR_EXPORT_LOGS = "axonius-export-logs"
DB_ADDR = 'mongo'


class BuildsManager(object):
    """Handles aws and db connections to provide data about instances, dockers, and VM's."""

    def __init__(self):
        """Initialize the object."""
        self.db = MongoClient(
            DB_ADDR,
            username='axonius',
            password='cqNLLfvQetvFog9y3iqi',
            connect=False
        ).builds
        self.bcm = BuildsCloudManager(CREDENTIALS_PATH)
        self.__exports_credentials = dict()
        self.__parse_credentials_file(CREDENTIALS_PATH)
        self.st = SlackNotifier()

        self.bypass_token = None
        with open(TOKENS_PATH, 'rt') as f:
            tokens = json.loads(f.read())
            for token, data in tokens.items():
                if data['builds_user_full_name'].lower() == 'builds':
                    self.bypass_token = token
                    break
        assert self.bypass_token, 'No bypass token found'

    def __parse_credentials_file(self, credentials_file_path: str):
        with open(credentials_file_path, 'rt') as f:
            credentials_file_contents = json.loads(f.read())

        self.__exports_credentials = credentials_file_contents['exports']['data']

    def get_instances(self, cloud=None, instance_id=None, vm_type=None):
        last_instances = self.db.realtime.find_one({'name': 'instances'})['value']
        if cloud:
            last_instances = [instance for instance in last_instances if instance['cloud']['cloud'] == cloud]
        if instance_id:
            last_instances = [instance for instance in last_instances if instance['cloud']['id'] == instance_id]
        if vm_type:
            last_instances = [
                instance for instance in last_instances
                if ((instance['cloud'].get('tags') or {}).get('VM-Type') or '').lower() == vm_type.lower() or
                   ((instance['cloud'].get('tags') or {}).get('vm-type') or '').lower() == vm_type.lower()
            ]

        return last_instances

    def update_instances_realtime(self):
        cloud_id_to_db = dict()
        for db_instance in self.db.instances.find({}):
            if db_instance.get('id'):
                cloud_id_to_db[db_instance['id']] = db_instance

        all_instances = []
        for cloud_instance in self.bcm.get_instances():
            all_instances.append(
                {
                    'cloud': cloud_instance,
                    'db': cloud_id_to_db.get(cloud_instance['id']) or {}
                }
            )

        # Sort by time of creation
        all_instances.sort(key=lambda x: datetime.datetime.now() if (x['db'] == {}) else x['db']['date'], reverse=True)

        self.db.realtime.update_one(
            {'name': 'instances'},
            {
                '$set': {
                    'value': all_instances
                }
            },
            upsert=True
        )

    def add_instances(
            self, cloud, vm_type, name, instance_type, num, image, key_name, public, code, network_security_options,
            owner, fork, branch
    ) -> (List[str], str):
        if public is True:
            generic, _ = self.bcm.create_public_instances(
                cloud, vm_type, name, instance_type, num, key_name, image, code, network_security_options
            )
        else:
            generic, _ = self.bcm.create_regular_instances(
                cloud, vm_type, name, instance_type, num, key_name, image, code, network_security_options
            )

        owner_full_name, owner_slack_id = owner
        instance_ids = [instance['id'] for instance in generic]
        group_name = f'{name}-' + str(time.time())
        for i, instance_id in enumerate(instance_ids):
            self.db.instances.insert_one(
                {
                    'cloud': cloud,
                    'id': instance_id,
                    'vm_type': vm_type,
                    'key_name': key_name,
                    'name': name if num == 1 else f'{name}-{i}',
                    'group_name': group_name,
                    'code': code,
                    'date': datetime.datetime.utcnow(),
                    'owner': owner_full_name,
                    'owner_slack_id': owner_slack_id,
                    'fork': fork,
                    'branch': branch
                }
            )
            self.update_last_user_interaction_time(cloud, instance_id)

        if image is not None:
            # We must let the realtime monitor update itself.
            time.sleep(10)
            for instance_generic in generic:
                instance_id = instance_generic['id']
                try:
                    instance_data = self.get_instances(cloud, instance_id)[0]
                except Exception:
                    # a second try.
                    time.sleep(10)
                    instance_data = self.get_instances(cloud, instance_id)[0]
                if network_security_options != NO_INTERNET_NETWORK_SECURITY_OPTION:
                    self.st.post_channel(
                        f'owner "{owner_full_name}" has raised an instance that will be connected to chef.',
                        channel='test_machines',
                        attachments=[self.st.get_instance_attachment(instance_data, [])])

        return generic, group_name

    def terminate_instance(self, cloud, instance_id):
        """Delete an instance by its id."""
        self.update_last_user_interaction_time(cloud, instance_id)
        self.bcm.terminate_instance(cloud, instance_id)
        self.db.instances.update_one({'cloud': cloud, 'id': instance_id}, {'$set': {'terminated': True, }})
        return True

    def terminate_group(self, group_name):
        # Note - this does not handle public ips!
        assert group_name
        instances = self.db.instances.find({'group_name': group_name})
        instances_by_cloud = {}
        for instance in instances:
            assert 'test' in instance['vm_type'].lower(), 'Do not ever use terminate_group on non-tests!'
            if instance['cloud'] not in instances_by_cloud:
                instances_by_cloud[instance['cloud']] = []

            if instance.get('terminated') is not True:
                instances_by_cloud[instance['cloud']].append(instance['id'])

        try:
            for cloud, instances_ids in instances_by_cloud.items():
                self.bcm.terminate_many_instances(cloud.lower(), instances_ids)
                for instance_id in instances_ids:
                    self.update_last_user_interaction_time(cloud, instance_id)
                    self.db.instances.update_one({'cloud': cloud, 'id': instance_id}, {'$set': {'terminated': True, }})
        except AssertionError as e:
            # This could happen if instances are already in a termination phase.
            # If instances are still not terminated for any reason, the instance monitor will try to terminate them.
            if 'not all nodes are terminated' not in str(e).lower():
                raise

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
        ssh.connect(AXONIUS_EXPORTS_SERVER, username=self.__exports_credentials['username'],
                    password=self.__exports_credentials['password'])
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
            "/usr/local/bin/packer build -force -var 'build_name={0}' -var 'fork={1}' -var 'branch={2}' -var 'image={3}' axonius_generate_installer.json >> build_{0}.log 2>&1".format(
                version, fork, branch, OVA_IMAGE_NAME),
            "git_hash=$(cat ./axonius_{0}_git_hash.txt)".format(version),
            "/usr/local/bin/packer build -force -var 'build_name={0}' -var 'fork={1}' -var 'branch={2}' -var 'image={3}' -var 'host_password={4}' axonius_install_system_and_provision.json >> build_{0}.log 2>&1".format(
                version, fork, branch, OVA_IMAGE_NAME, self.__exports_credentials['password']),
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

    def get_export_running_log(self, export_version):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(AXONIUS_EXPORTS_SERVER, username=self.__exports_credentials['username'],
                    password=self.__exports_credentials['password'])
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
        gce_name_match = re.search('Creating GCE image (.*)...$', log, re.MULTILINE)
        gce_name = gce_name_match.group(1) if gce_name_match else ''
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
                        'gce_name': gce_name,
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
