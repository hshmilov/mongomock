"""Defines the BuildsManager class which handles all connections to the db and amazon.

This project assumes the aws settings & credentials are already configured in the machine, either by using aws cli
(aws configure) or by putting it in "~/.aws.config"
"""
import datetime
import time
import json
from typing import List

import requests

from pymongo import MongoClient, DESCENDING

from buildscloud.builds_cloud_consts import NO_INTERNET_NETWORK_SECURITY_OPTION
from buildscloud.builds_cloud_manager import BuildsCloudManager
from config import TOKENS_PATH, CREDENTIALS_PATH, LOCAL_BUILDS_HOST
from slacknotifier import SlackNotifier


KEY_NAME = "Builds-VM-Key"  # The key we use for identification.

HD_SIZE_FOR_INSTANCE_IN_GIB = 100
HD_SIZE_FOR_INSTANCE_IN_GIB_FOR_EXPORT_BASED_INSTANCES = 196

S3_BUCKET_NAME_FOR_OVA = "axonius-releases"
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

        self.__teamcity_credentials = credentials_file_contents['teamcity']['data']

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
            owner, fork, branch, tunnel, base_instance
    ) -> (List[str], str):
        if public is True:
            generic, _ = self.bcm.create_public_instances(
                cloud, vm_type, name, instance_type, num, key_name, image, code, network_security_options
            )
        else:
            generic, _ = self.bcm.create_regular_instances(
                cloud, vm_type, name, instance_type, num, key_name, image, code, network_security_options, tunnel,
                base_instance
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

        if image is not None and owner_full_name != 'Auto-Tests':
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

    def get_export_by_version(self, version):
        return self.db.exports.find_one({'version': version})

    def get_exports(self, status=None, limit=0):
        """Return all vm exports we have on our s3 bucket."""
        if status is None:
            # Even though we don't support deletions now, let's not show old deleted exports.
            exports = self.db.exports.find({'status': {"$nin": ["deleted"]}}, {"_id": 0}) \
                .sort('_id', DESCENDING). \
                limit(limit)
        else:
            exports = self.db.exports.find({'status': {"$in": status}}, {"_id": 0}) \
                .sort('_id', DESCENDING) \
                .limit(limit)

        return list(exports)

    def _teamcity_export_ova(self, name, owner, fork, branch, client_name, disk_size, comments):
        tc_user = self.__teamcity_credentials['username']
        tc_pass = self.__teamcity_credentials['password']

        response = requests.post(url='https://teamcity-local.axonius.lan/httpAuth/app/rest/buildQueue',
                                 auth=(tc_user, tc_pass),
                                 json={"buildType": {"id": "Devops_Exports_Installer"},
                                       "properties": {
                                           "property": [{"name": "branch", "value": branch},
                                                        {"name": "client_name", "value": client_name},
                                                        {"name": "teamcity.build.triggeredBy.username", "value": owner},
                                                        {"name": "fork", "value": fork},
                                                        {"name": "disk_size", "value": disk_size},
                                                        {"name": "comments", "value": comments},
                                                        {"name": "name", "value": name}
                                                        ]}},
                                 headers={'Content-Type': 'application/json',
                                          'Accept': 'application/json'},
                                 verify=False)
        response.raise_for_status()

    def export_ova(self, version, owner, fork, branch, client_name, comments, disk_size):
        owner_full_name, owner_slack_id = owner

        self._teamcity_export_ova(version, owner_full_name, fork, branch, client_name, disk_size, comments)

        db_json = dict()
        db_json['version'] = version
        db_json['owner'] = owner_full_name
        db_json['owner_slack_id'] = owner_slack_id
        db_json['fork'] = fork
        db_json['branch'] = branch
        db_json['client_name'] = client_name
        db_json['comments'] = comments
        db_json['date'] = datetime.datetime.utcnow()

        self.db.exports.update_one(
            {'version': version},
            {
                '$setOnInsert': {'status': 'InProgress'},
                '$set': db_json
            },
            upsert=True
        )
        return True

    def update_export_from_teamcity_hook(self, request_params):
        translation = {'name': 'version', 'owner': 'owner', 'fork': 'fork', 'branch': 'branch', 'comments': 'comments',
                       'installer_git_hash': 'git_hash', 'artifact.amazon-ebs': 'ami_id', 'artifact.googlecompute': 'gce_name',
                       's3_qemu': 's3_qcow3', 's3_vhdx': 's3_vhdx',
                       'ami_log': 'ami_log', 'ova_log': 'ova_log', 'ova_test_log': 'ova_test_log', 'installer_log': 'installer_log',
                       's3_installer': 'installer_download_link', 'ami_test_log': 'ami_test_log', 'ami_test_return_code': 'ami_test_return_code',
                       'ova_test_return_code': 'ova_test_return_code', 'cloud_log': 'cloud_log',
                       's3_ova': 'download_link', 'client_name': 'client_name', 'log': 'log'}

        db_set_entry = {}
        for (k, translated_key) in translation.items():
            value = request_params.get(k)
            if value is not None:
                db_set_entry[translated_key] = value

        db_set_entry['date'] = datetime.datetime.now()
        # TODO: This isn't the full log, as there is no full log, it will always be the latest build log.

        # TODO: There might be a race condition here.
        db_old_export = self.db.exports.find_one({'version': db_set_entry['version']}) or {}

        db_old_export_updated = dict(db_old_export)
        db_old_export_updated.update(db_set_entry)

        return_codes_to_check = {'ami_test_return_code', 'ova_test_return_code'}

        # None for unspecified.
        actual_return_codes = [db_old_export_updated.get(return_code, None) for return_code in return_codes_to_check]

        if all(r == 0 for r in actual_return_codes):
            new_status = 'completed'
        elif any((r is not None and r != 0) for r in actual_return_codes):
            new_status = 'failed'
        elif request_params.get('status') == 'failure':
            new_status = 'failed'
        elif db_old_export.get('status') == 'failure':
            new_status = 'failed'
        else:
            new_status = 'InProgress'

        db_set_entry['status'] = new_status

        self.db.exports.update_one(
            {'version': db_set_entry['version']},
            {
                '$set': db_set_entry
            },
            upsert=True
        )

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
