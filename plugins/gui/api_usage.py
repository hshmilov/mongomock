#!/usr/bin/env python36
# XXX: do not import from axonius libs here
import argparse
import logging
import pprint
import typing

import requests

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


DEFAULT_AXONIUS_URL = 'https://localhost'
AXONIUS_API = '/api/V1'

DEFAULT_USERNAME = 'admin'

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


class ArgumentParser(argparse.ArgumentParser):
    """ Argumentparser for the script """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formatter_class = argparse.RawDescriptionHelpFormatter
        self.description = \
            '''Example:
  %(prog)s -x https://axnoius.local --username admin -p password1 --function get_devices_example1
  %(prog)s -x https://axnoius.local --username admin -p password1 --all-functions'''

        action_group = self.add_mutually_exclusive_group(required=True)
        action_group.add_argument('--function', choices=RESTExample.get_examples())
        action_group.add_argument('--all-functions', action='store_true', default=False, help='Run all functions')

        self.add_argument('--axonius-url', '-x', default=DEFAULT_AXONIUS_URL)
        self.add_argument('--username', '-u', default=DEFAULT_USERNAME)
        self.add_argument('--password', '-p', required=True)
        self.add_argument('--no-verify-ssl', '-s', action='store_true', default=False,
                          help='Don\'t verify ssl')

        self.add_argument('--logfile', '-l')


class RESTClient:
    """ simple rest client for Axonius REST API """

    def __init__(self, axonius_url, username,
                 password, **kwargs):
        self._url = axonius_url
        self._username = username
        self._password = password
        self._request_args = kwargs

        self._logger = logging.getLogger('RESTClient')

    def do_request(self, action: str, url: str, **kwargs):
        """ Sends axnoius rest api to the server """
        kwargs.update(self._request_args)
        kwargs.update({'auth': (self._username, self._password)})

        full_url = f'{self._url}{AXONIUS_API}{url}'
        resp = requests.request(action,
                                full_url,
                                **kwargs)

        self._logger.info(resp.status_code)
        # Only if we have content print the json
        if resp.status_code == 200 and resp.content:
            data = resp.json()
            self._logger.info(pprint.pformat(data))
        else:
            data = resp.text
            self._logger.info(data)

        return (resp.status_code, data)

    def get_devices(self, skip: int, limit: int, fields=None, filter_=None):
        params = {}
        params['skip'] = skip
        params['limit'] = limit

        if fields:
            params['fields'] = fields
        if filter_:
            params['filter'] = filter_

        return self.do_request('get', '/devices', params=params)

    def get_device_by_id(self, device_id: str):
        return self.do_request('get', f'/devices/{device_id}')

    def get_devices_views(self, skip: int, limit: int, filter_: str):
        params = {}
        params['limit'] = 1000
        params['skip'] = 0
        params['filter'] = filter_
        return self.do_request('get', '/devices/views', params=params)

    def create_new_device_view(self, name: str, view: dict, query_type: str):
        data = {
            'name': name,
            'view': view,
            'query_type': query_type,
        }
        return self.do_request('post', '/devices/views', json=data)

    def delete_devices_views(self, device_id: list):
        # Deletes all listed device views (by ID).
        return self.do_request('delete', '/devices/views', json=device_id)

    def get_users(self, skip: str, limit: str, fields=None, filter_=None):
        params = {}
        params['skip'] = skip
        params['limit'] = limit

        if fields:
            params['fields'] = fields
        if filter_:
            params['filter'] = filter_
        return self.do_request('get', '/users', params=params)

    def get_user_by_id(self, user_id: str):
        return self.do_request('get', f'/users/{user_id}')

    def get_users_views(self, skip: str, limit: str, filter_: list=None):

        params = {}

        params['limit'] = limit
        params['skip'] = skip
        if filter_:
            params['filter'] = filter_

        return self.do_request('get', '/users/views', params=params)

    def create_new_user_view(self, name: str, view: dict, query_type: str):
        data = {
            'name': name,
            'view': view,
            'query_type': query_type,
        }
        return self.do_request('post', '/users/views', json=data)

    def delete_users_views(self, user_ids: list):
        # Deletes all listed device views (by ID).
        data = user_ids
        return self.do_request('delete', '/users/views', json=data)

    def get_alerts(self, skip: int=None, limit: int=None, fields: list=None):
        params = {
            'skip': skip,
            'limit': limit,
            'fields': fields
        }

        # This will get all the configured alerts
        return self.do_request('get', '/alerts', params=params)

    def delete_alerts(self, alert_ids: list):
        return self.do_request('delete', '/alerts', json=alert_ids)

        # Response would be status code 200 (OK)

    def put_alert(self,
                  name: int,
                  triggers: dict,
                  period: str,
                  actions: list,
                  view: str,
                  viewEntity: str,
                  severity: str,
                  retrigger: bool=True,
                  triggered: bool=False):
        # Notice that id = "new" tells the api this is a new alert.
        # Triggers should contain all the triggers with true (or int above 0) on activated triggers.
        # Actions type should be one of thses:
        # tag_entities
        # create_service_now_computer
        # create_service_now_incident
        # notify_syslog
        # send_emails
        # create_notification
        # tag_entities

        data = {'id': 'new',
                'name': name,
                'triggers': triggers,
                'period': period,
                'actions': actions,
                'view': view,
                'viewEntity': viewEntity,
                'retrigger': retrigger,
                'triggered': triggered,
                'severity': 'warning'}

        return self.do_request('put', '/alerts', json=data)

    def get_actions(self):
        return self.do_request('get', '/actions')

    def run_action(self, device_ids: list, action_name: str, command: str):
        data = {
            'internal_axon_ids': device_ids,  # The devices
            'action_name': action_name,
            'command': command,
        }

        return self.do_request('post', '/actions/shell', json=data)

    def deploy_action(self, device_ids: list, action_name: str, binary_uuid: str, binary_filename: str,
                      params: str=''):
        data = {
            'internal_axon_ids': device_ids,  # The device
            'action_name': action_name,
            'binary': {'filename': binary_filename,
                       'uuid': binary_uuid}
        }
        if params:
            data['params'] = params

        return self.do_request('post', '/actions/deploy', json=data)

    def get_devices_labels(self):
        """ returns a list of strings that are the devices labels in the system """
        return self.do_request('get', '/devices/labels')

    def get_users_labels(self):
        """ returns a list of strings that are the users labels in the system """
        return self.do_request('get', '/users/labels')

    def add_labels(self, entities: list, labels: list):
        data = {
            'entities': {
                'ids': entities,  # list of internal axon ids
            },
            'labels': labels      # list of labels to add
        }
        return self.do_request('post', '/devices/labels', json=data)

    def delete_labels(self,  entities: list, labels: list):
        data = {
            'entities': {
                'ids': entities,
            },                     # list of internal axon ids
            'labels': labels       # list of labels to add
        }
        return self.do_request('delete', '/devices/labels', json=data)

    def upload_file(self, binary: typing.io.BinaryIO):
        """ Upload a file to the system, that later can be use for deployment """
        return self.do_request('post', '/actions/upload_file', data={'field_name': 'binary'},
                               files={'userfile': ('example_filename', binary)})


class RESTExample:
    """ class that implement Axonius REST API usage.
        note: the examples assumes that there are at least one user and one device in the system with
              and execution and device_control enabled"""

    def __init__(self, axonius_url, username,
                 password, verify_ssl):
        self._client = RESTClient(axonius_url,
                                  username,
                                  password,
                                  verify=verify_ssl)
        self._logger = logging.getLogger('RESTExample')

    @classmethod
    def get_examples(cls):
        examples_functions = (cls.get_devices1,
                              cls.get_devices2,
                              cls.get_device_by_id,
                              cls.get_devices_views,
                              cls.create_and_delete_device_view,
                              cls.get_users,
                              cls.get_user_by_id,
                              cls.create_and_delete_user_view,
                              cls.get_alerts,
                              cls.create_and_delete_alert,
                              cls.get_actions,
                              cls.deploy_action,
                              cls.run_action,
                              cls.get_users_labels,
                              cls.get_devices_labels,
                              cls.add_and_delete_labels)
        return [function.__name__ for function in examples_functions]

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
                                                       viewEntity='users',
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

    def get_users_labels(self):
        status_code, labels = self._client.get_users_labels()
        assert status_code == 200
        assert isinstance(labels, list)

    def add_and_delete_labels(self):
        # Fetch some devices to find any id for the exmaple
        status_code, devices = self._client.get_devices(limit=2, skip=0)
        assert status_code == 200, 'Failed to fetch devices'

        device_example = devices['assets'][0]
        device_id = device_example['internal_axon_id']

        entities = [device_id]
        labels = ['Example Label']

        status_code, resp = self._client.add_labels(entities, labels)
        assert status_code == 200

        self._logger.info(f'Fetching device id: {device_id}')
        status_code, device = self._client.get_device_by_id(device_id)
        assert status_code == 200, 'Failed to fetch device by id'

        assert 'Example Label' in device['labels'], 'Failed to add label %s' % device['labels']

        status_code, resp = self._client.delete_labels(entities, labels)
        assert status_code == 200

        self._logger.info(f'Fetching device id: {device_id}')
        status_code, device = self._client.get_device_by_id(device_id)
        assert status_code == 200, 'Failed to fetch device by id'

        assert 'Example Label' not in device['labels'], 'Failed to delete label'


def main():
    requests.packages.urllib3.disable_warnings()
    args = ArgumentParser().parse_args()
    logging.basicConfig(format='%(message)s', level=logging.INFO, filename=args.logfile)

    client = RESTExample(args.axonius_url,
                         args.username,
                         args.password,
                         not args.no_verify_ssl)
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
