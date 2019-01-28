#!/usr/bin/env python36
import logging

from axoniussdk import argument_parser
from axoniussdk.client import RESTClient

__author__ = 'Axonius, Inc'


class ArgumentParser(argument_parser.ArgumentParser):
    """ Argumentparser for the script """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        action_group = self.add_mutually_exclusive_group(required=True)
        action_group.add_argument('--function', choices=RESTExample.get_examples())
        action_group.add_argument('--all-functions', action='store_true', default=False, help='Run all functions')
        self.description = \
            '''Example:
  %(prog)s -x https://axonius.local --username admin -p password1 --no-verify-ssl --function get_devices1
  %(prog)s -x https://axonius.local --api-key xxxx --api-secret yyyy --all-functions'''


TRIGGERS_DEFAULT_VALUES = {'every_discovery': False,
                           'new_entities': False,
                           'previous_entities': False,
                           'above': 0,
                           'below': 0,
                           }

ACTION_PUT_FILE = 'Touch Axonius File'
PUT_FILE_EXAMPLE = 'echo \'Touched by axonius\' > /home/ubuntu/axonius_file'

ACTION_RUN_SCRIPT = 'Echo Hello'
ACTION_RUN_FILENAME = 'example.sh'
RUN_SCRIPT_EXAMPLE = b'#!/bin/bash\necho hello world!'


AXONIUS_API = '/api/V1'

DEVICE_VIEW_NAME = 'All Nexpose Scanned AD Devices Example'
DEVICE_VIEW_VIEW = {'page': 0,
                    'pageSize': 20,
                    'fields': ['adapters', 'specific_data.data.hostname',
                               'specific_data.data.name',
                               'specific_data.data.os.type',
                               'specific_data.data.network_interfaces.ips',
                               'specific_data.data.network_interfaces.mac',
                               'labels'],
                    'coloumnSizes': [],
                    'query': {
                        'filter': 'adapters == \"active_directory_adapter\" and adapters == \"nexpose_adapter\"',
                        'expressions': [
                            {'logicOp': '', 'not': False,
                             'leftBracket': False,
                             'field': 'adapters',
                             'compOp': 'equals',
                             'value': 'active_directory_adapter',
                             'rightBracket': False,
                             'i': 0},
                            {'logicOp': 'and',
                             'not': False,
                             'leftBracket': False,
                             'field': 'adapters',
                             'compOp': 'equals',
                             'value': 'nexpose_adapter',
                             'rightBracket': False,
                             'i': 1}]},
                    'sort': {'field': '', 'desc': True}}
DEVICE_VIEW_QUERY_TYPE = 'saved'
USER_VIEW_NAME = 'Not Local Users Example'
USER_VIEW_VIEW = {'page': 0, 'pageSize': 20,
                  'historical': 'null',
                  'fields': ['specific_data.data.image',
                             'specific_data.data.username',
                             'specific_data.data.domain',
                             'specific_data.data.last_seen',
                             'specific_data.data.is_admin',
                             'specific_data.data.last_seen_in_devices'],
                  'coloumnSizes': [],
                  'query': {'filter': 'specific_data.data.is_local == \'True\'',
                            'expressions': [
                                {'compOp': 'True',
                                 'field': 'specific_data.data.is_local',
                                 'i': 0,
                                 'leftBracket': False,
                                 'logicOp': '',
                                 'not': False,
                                 'rightBracket': False,
                                 'value': ''}]},
                  'sort': {'desc': True, 'field': ''}}
USER_VIEW_QUERY_TYPE = 'saved'

ALERT_NAME = 'Test Alert 3'


class RESTExample:
    """ class that implement Axonius REST API usage.
        note: the examples assumes that there are at least one user and one device in the system with
              and execution and device_control enabled"""

    def __init__(self, axonius_url, **kwargs):
        self._client = RESTClient(axonius_url, **kwargs)
        self._logger = logging.getLogger('RESTExample')

    @classmethod
    def get_examples(cls):
        examples_functions = (cls.get_devices1,
                              cls.get_devices2,
                              cls.get_devices_count,
                              cls.get_device_by_id,
                              cls.get_devices_views,
                              cls.create_and_delete_device_view,
                              cls.get_users,
                              cls.get_users_count,
                              cls.get_user_by_id,
                              cls.get_users_views,
                              cls.create_and_delete_user_view,
                              cls.get_alerts,
                              cls.create_and_delete_alert,
                              cls.get_actions,
                              cls.deploy_action,
                              cls.run_action,
                              cls.get_users_labels,
                              cls.get_devices_labels,
                              cls.add_and_delete_devices_labels,
                              cls.add_and_delete_users_labels,
                              cls.get_adapters,
                              cls.check_connectivity,
                              cls.add_and_delete_client)

        examples_functions = {function.__name__ for function in examples_functions}
        all_examples_functions = set(filter(lambda x: 'get_examples' not in x and not x.startswith('__'),
                                            dir(cls)))

        # just validate that we didn't forget any example
        assert all_examples_functions == examples_functions, all_examples_functions - examples_functions

        return examples_functions

    def get_devices1(self):
        # This would query a max of 50 devices with no filters on either the devices themselves or their fields
        # and will skip the first 20 devices.
        status_code, devices = self._client.get_devices(skip=20, limit=50)
        assert status_code == 200, 'failed to get devices'
        # The request would look like this
        # https://localhost/api/V1/devices?limit=50&skip=20

    def get_devices2(self):
        # This will tell the api to bring these specific fields.
        fields = ','.join(
            ['adapters', 'specific_data.data.hostname', 'specific_data.data.name', 'specific_data.data.os.type',
             'specific_data.data.network_interfaces.ips', 'specific_data.data.network_interfaces.mac', 'labels'])

        # This a url encoded filter that brings all the devices that were correlated from
        # Rapid 7 Nexpose and Active Directory adapters.
        # adapters%20==%20%22active_directory_adapter%22%20and%20adapters%20==%20%22nexpose_adapter%22
        filter_ = 'adapters == "active_directory_adapter" and adapters == "nexpose_adapter"'

        # The request would look like this
        # https://localhost/api/V1/devices?skip=0&limit=50&fields=adapters,specific_data.data.hostname,specific_data.data.name,specific_data.data.os.type,specific_data.data.network_interfaces.ips,specific_data.data.network_interfaces.mac,labels&filter=adapters%20==%20%22active_directory_adapter%22%20and%20adapters%20==%20%22nexpose_adapter%22
        status_code, devices = self._client.get_devices(skip=0, limit=50, fields=fields, filter_=filter_)
        assert status_code == 200, 'failed to get devices'

    def get_device_by_id(self):
        # Fetch some devices to find any id for the exmaple
        status_code, devices = self._client.get_devices(limit=2, skip=0)
        assert status_code == 200, 'Failed to fetch devices'

        device_example = devices['assets'][0]
        device_id = device_example['internal_axon_id']

        self._logger.info(f'Fetching device id: {device_id}')
        status_code, device = self._client.get_device_by_id(device_id)
        assert status_code == 200, 'Failed to fetch device by id'

        # we should get the same device
        assert device_example['internal_axon_id'] == device['internal_axon_id']

    def get_devices_views(self):
        # https://localhost/api/devices/views?limit=1000&skip=0&filter=query_type==%27saved%27
        status_code, device_views = self._client.get_devices_views(skip=0, limit=1000, filter_='query_type==\'saved\'')
        assert status_code == 200, 'failed to create new device view'

    def create_and_delete_device_view(self):
        # Creates a new saved query named: "All Nexpose Scanned AD Devices" That gets all the devices that have been
        # queried from both Rapid 7 Nexpose and Active Directory
        status_code, id_ = self._client.create_new_device_view(DEVICE_VIEW_NAME,
                                                               DEVICE_VIEW_VIEW,
                                                               DEVICE_VIEW_QUERY_TYPE)
        assert status_code == 200, 'failed to create new device view'
        assert len(id_) == 24 or len(id_) == 12, 'failed to get device view id'

        # Validate that the saved query created
        status_code, device_views = self._client.get_devices_views(skip=0,
                                                                   limit=1,
                                                                   filter_=f'name==\'{DEVICE_VIEW_NAME}\'')
        assert status_code == 200, 'failed find the device view'
        assert device_views['page']['totalResources'] == 1, 'Unable to find device view'

        # Delete the saved query
        self._logger.info(f'deleteing view id: {id_}')
        status_code, _ = self._client.delete_devices_views([id_])
        assert status_code == 200, 'failed to delete the new device view'

        # Validate that the saved query was deleted
        status_code, device_views = self._client.get_devices_views(skip=0,
                                                                   limit=1,
                                                                   filter_=f'name==\'{DEVICE_VIEW_NAME}\'')
        assert status_code == 200, 'failed find the device view'
        assert device_views['page']['totalResources'] == 0, 'Device view still exists'

    def get_users(self):
        skip = 0
        limit = 20

        # This will tell the api to bring these specific fields.
        fields = ','.join(
            ['specific_data.data.image', 'specific_data.data.username', 'specific_data.data.domain',
             'specific_data.data.last_seen', 'specific_data.data.is_admin'])

        filter_ = 'specific_data.data.is_local == false'

        # This a url encoded filter that brings all the not local users.
        # specific_data.data.is_local%20==%20false
        # https://localhost/api/V1/users?skip=0&limit=20&fields=specific_data.data.image,specific_data.data.username,specific_data.data.domain,specific_data.data.last_seen,specific_data.data.is_admin&filter=specific_data.data.is_local%20==%20false

        status_code, users = self._client.get_users(skip, limit, fields, filter_)
        assert status_code == 200, 'Failed to fetch client'

    def get_user_by_id(self):
        # Fetch some users to find any id for the exmaple
        status_code, users = self._client.get_users(limit=2, skip=0)
        assert status_code == 200, 'Failed to fetch users'

        user_example = users['assets'][0]
        user_id = user_example['internal_axon_id']

        self._logger.info(f'Fetching user id: {user_id}')
        status_code, user = self._client.get_user_by_id(user_id)
        assert status_code == 200, 'Failed to fetch user by id'

        # we should get the same user
        assert user_example['internal_axon_id'] == user['internal_axon_id']

    def get_users_views(self):
        # https://localhost/api/users/views?limit=1000&skip=0&filter=query_type==%27saved%27
        status_code, views = self._client.get_users_views(0, 1000, 'query_type==\'saved\'')
        assert status_code == 200, 'Failed to fetch user by id'

    def create_and_delete_user_view(self):
        # Creates a new saved query named
        status_code, id_ = self._client.create_new_user_view(USER_VIEW_NAME, USER_VIEW_VIEW, USER_VIEW_QUERY_TYPE)
        assert status_code == 200, 'failed to create new user view'
        assert len(id_) == 24 or len(id_) == 12, 'failed to get user view id'

        # Validate that the saved query created
        status_code, user_views = self._client.get_users_views(skip=0, limit=1, filter_=f'name==\'{USER_VIEW_NAME}\'')
        assert status_code == 200, 'failed find the user view'
        assert user_views['page']['totalResources'] == 1, 'Unable to find user'

        # Delete the saved query
        self._logger.info(f'deleteing view id: {id_}')
        status_code, _ = self._client.delete_users_views([id_])
        assert status_code == 200, 'failed delete the user view'

        # Validate that the saved query was deleted
        status_code, user_views = self._client.get_users_views(skip=0, limit=1, filter_=f'name==\'{USER_VIEW_NAME}\'')
        assert status_code == 200, 'failed find the user view'
        assert user_views['page']['totalResources'] == 0, 'user saved query still exists'

    def get_alerts(self):
        # https://localhost/api/alert?skip=NaN&limit=0&fields=name,report_creation_time,triggered,view,severity
        fields = ['name', 'report_creation_time', 'triggered', 'view', 'severity']
        status_code, alerts = self._client.get_alerts(fields=','.join(fields))
        assert status_code == 200, 'Failed to get alerts'

    def create_and_delete_alert(self):
        trigger_dict = TRIGGERS_DEFAULT_VALUES
        trigger_dict['above'] = 1

        # Create new alert
        status_code, alert_id = self._client.put_alert(name=ALERT_NAME,
                                                       triggers=trigger_dict,
                                                       period='weekly',
                                                       actions=[{'type': 'create_notification'}],
                                                       view='Users Created in Last 30 Days',
                                                       view_entity='users',
                                                       severity='warning')

        assert status_code == 201, 'Failed to create new alert'
        assert len(alert_id) in [12, 24], 'Failed to get alert id'

        # validate that the alert exists
        status_code, alerts = self._client.get_alerts(fields='name')
        names = [alert['name'] for alert in alerts['assets']]
        assert status_code == 200, 'Failed to get alert'
        assert ALERT_NAME in names, 'Failed to find our alert name'

        # delete alert
        status_code, resp = self._client.delete_alerts([alert_id])
        assert status_code == 200, 'Unable to delete alerts'
        assert resp == '', 'invalid response'

        # validate that the alert exists
        status_code, alerts = self._client.get_alerts(fields='name')
        names = [alert['name'] for alert in alerts['assets']]
        assert status_code == 200, 'Failed to get alert'
        assert ALERT_NAME not in names, 'Alert still in alerts'

    def get_actions(self):
        status_code, actions = self._client.get_actions()
        assert status_code == 200
        assert isinstance(actions, list)
        assert 'deploy' in actions
        assert 'shell' in actions
        assert 'upload_file' in actions

    def run_action(self):
        """ This action gets shell command as input and execute it."""

        # Fetch some devices to find any id for the exmaple
        status_code, devices = self._client.get_devices(limit=2, skip=0)
        assert status_code == 200, 'Failed to fetch devices'

        device_example = devices['assets'][0]
        device_id = device_example['internal_axon_id']

        status_code, _ = self._client.run_action(device_ids=[device_id],   # The devices
                                                 action_name=ACTION_PUT_FILE,  # The action name - will be shown as tag
                                                 command=PUT_FILE_EXAMPLE)
        assert status_code == 200

    def deploy_action(self):
        """ This action takes binary file and execute it.
            In the following example we pass bash script as the file"""

        # Fetch some devices to find any id for the exmaple
        status_code, devices = self._client.get_devices(limit=2, skip=0)
        assert status_code == 200, 'Failed to fetch devices'

        device_example = devices['assets'][1]
        device_id = device_example['internal_axon_id']

        # Now we need to upload the binary file
        self._logger.info('Uploading file')
        status_code, resp = self._client.upload_file(RUN_SCRIPT_EXAMPLE)
        assert status_code == 200
        assert 'uuid' in resp

        uuid = resp['uuid']

        status_code, _ = self._client.deploy_action(device_ids=[device_id],  # The devices
                                                    action_name=ACTION_RUN_SCRIPT,
                                                    binary_filename=ACTION_RUN_FILENAME,
                                                    binary_uuid=uuid)
        assert status_code == 200

    def get_devices_labels(self):
        status_code, labels = self._client.get_devices_labels()
        assert status_code == 200
        assert isinstance(labels, list)

    def get_devices_count(self):
        status_code, count = self._client.get_devices_count('adapters == \"active_directory_adapter\"')
        assert status_code == 200
        assert isinstance(count, int)

    def get_users_count(self):
        status_code, count = self._client.get_users_count()
        assert status_code == 200
        assert isinstance(count, int)

    def get_users_labels(self):
        status_code, labels = self._client.get_users_labels()
        assert status_code == 200
        assert isinstance(labels, list)

    def add_and_delete_devices_labels(self):
        # Fetch some devices to find any id for the exmaple
        status_code, devices = self._client.get_devices(limit=2, skip=0)
        assert status_code == 200, 'Failed to fetch devices'

        device_example = devices['assets'][0]
        device_id = device_example['internal_axon_id']

        entities = [device_id]
        labels = ['Example Label']

        status_code, resp = self._client.add_devices_labels(entities, labels)
        assert status_code == 200

        self._logger.info(f'Fetching device id: {device_id}')
        status_code, device = self._client.get_device_by_id(device_id)
        assert status_code == 200, 'Failed to fetch device by id'

        assert 'Example Label' in device['labels'], 'Failed to add label %s' % device['labels']

        status_code, resp = self._client.delete_devices_labels(entities, labels)
        assert status_code == 200

        self._logger.info(f'Fetching device id: {device_id}')
        status_code, device = self._client.get_device_by_id(device_id)
        assert status_code == 200, 'Failed to fetch device by id'

        assert 'Example Label' not in device['labels'], 'Failed to delete label'

    def add_and_delete_users_labels(self):
        # Fetch some users to find any id for the exmaple
        status_code, users = self._client.get_users(limit=2, skip=0)
        assert status_code == 200, 'Failed to fetch users'

        user_example = users['assets'][0]
        user_id = user_example['internal_axon_id']

        entities = [user_id]
        labels = ['Example Label']

        status_code, resp = self._client.add_users_labels(entities, labels)
        assert status_code == 200

        self._logger.info(f'Fetching user id: {user_id}')
        status_code, user = self._client.get_user_by_id(user_id)
        assert status_code == 200, 'Failed to fetch user by id'

        assert 'Example Label' in user['labels'], 'Failed to add label %s' % user['labels']

        status_code, resp = self._client.delete_users_labels(entities, labels)
        assert status_code == 200

        self._logger.info(f'Fetching user id: {user_id}')
        status_code, user = self._client.get_user_by_id(user_id)
        assert status_code == 200, 'Failed to fetch user by id'

        assert 'Example Label' not in user['labels'], 'Failed to delete label'

    def get_adapters(self):
        status_code, adapters = self._client.get_adapters()
        assert status_code == 200, 'Failed to get adapter and client list'

        nodes = adapters['active_directory_adapter']
        master_node = list(filter(lambda node: node['node_name'] == 'Master', nodes))[0]

        node_id = master_node['node_id']

        assert master_node['clients'], 'No clients in master node'

    def check_connectivity(self):
        status_code, adapters = self._client.get_adapters()
        assert status_code == 200, 'Failed to get adapter and client list'

        assert 'active_directory_adapter' in adapters

        nodes = adapters['active_directory_adapter']
        master_node = list(filter(lambda node: node['node_name'] == 'Master', nodes))[0]

        node_id = master_node['node_id']

        first_client = master_node['clients'][0]['client_config']

        status_code, resp = self._client.check_connectivity('active_directory_adapter', first_client, node_id)
        assert status_code == 200, resp

        first_client['dc_name'] = 'fail'
        status_code, resp = self._client.check_connectivity('active_directory_adapter', first_client, node_id)
        assert status_code == 500, resp

    def add_and_delete_client(self):
        status_code, adapters = self._client.get_adapters()
        adapter_name = 'active_directory_adapter'

        nodes = adapters[adapter_name]
        master_node = list(filter(lambda node: node['node_name'] == 'Master', nodes))[0]
        node_id = master_node['node_id']

        client_config = {
            'dc_name': 'example',
            'fetch_disabled_devices': False,
            'fetch_disabled_users': False,
            'password': 'example_password',
            'user': 'example_user',
        }

        status_code, resp = self._client.add_client(adapter_name, client_config, node_id)
        assert status_code == 200, resp
        id_ = resp['id']

        self._logger.info(f'deleting client id : {id_}')

        status_code, resp = self._client.delete_client(adapter_name, id_, node_id)
        assert status_code == 200, resp


def main():
    args = ArgumentParser().parse_args()
    logging.basicConfig(format='%(message)s', level=logging.INFO, filename=args.logfile)

    client = RESTExample(args.axonius_url,
                         auth=args.auth,
                         headers=args.headers,
                         verify=not args.no_verify_ssl)
    if args.function:
        logging.info(f'Calling api function "{args.function}"')
        callback = getattr(client, args.function)
        callback()

    if args.all_functions:
        for name in client.get_examples():
            logging.info(f'Calling api function "{name}"')
            callback = getattr(client, name)
            callback()
            logging.info('\n\n')


if __name__ == '__main__':
    main()
