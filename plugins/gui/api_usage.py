#!/usr/bin/env python36
# XXX: do not import from axonius libs here
import argparse
import logging

import requests
from requests.models import Response

TRIGGERS_DEFAULT_VALUES = {'every_discovery': False,
                           'new_entities': False,
                           'previous_entities': False,
                           'above': 0,
                           'below': 0,
                           }

ACTION_PUT_FILE = 'Put File'
ACTION_RUN_SCRIPT = 'Run Script File'

PUT_FILE_EXAMPLE = 'echo \'Touched by axonius\' > /home/ubuntu/axonius_file'
RUN_SCRIPT_EXAMPLE = '#!/bin/bash\necho hello world!'


DEFAULT_AXONIUS_URL = 'https://localhost'
AXONIUS_API = '/api/V1'

DEFAULT_USERNAME = 'admin'


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


class RESTClient:
    """ simple rest client for Axonius REST API """

    def __init__(self, axonius_url, username,
                 password, **kwargs):
        self._url = axonius_url
        self._username = username
        self._password = password
        self._request_args = kwargs

        self._logger = logging.getLogger('RESTClient')

    def do_request(self, action: str, url: str, **kwargs) -> Response:
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
            self._logger.info(resp.json())
        else:
            self._logger.info(resp.text)

        return resp

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

    def delete_device_view(self, device_id: str):
        # Deletes all listed device views (by ID).
        data = [device_id]
        return self.do_request('delete', '/devices/views', json=data)

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
        return self.do_request('get', f'/devices/{user_id}')

    def get_users_view(self, skip: str, limit: str, filter_: list=None):

        params = {}

        params['limit'] = limit
        params['skip'] = skip
        if filter_:
            params['filter'] = filter_

        return self.do_request('get', '/users/views', params=params)

    def save_users_view(self, name: str, view: dict, query_type: str):
        data = {
            'name': name,
            'view': view,
            'query_type': query_type,
        }
        return self.do_request('post', '/users/views', json=data)

    def delete_user_view(self, user_ids: list):
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

    def shell_action(self, device_ids: list, action_name: str, command: str):
        data = {
            'internal_axon_ids': device_ids,  # The devices
            'action_name': action_name,
            'command': command,
        }

        return self.do_request('post', '/actions/shell', json=data)

    def deploy_action(self, device_ids: list, action_name: str, binary: str):
        data = {
            'internal_axon_ids': device_ids,  # The device
            'action_name': action_name,
            'binary': binary,
        }

        return self.do_request('post', '/actions/deploy', json=data)

    def get_devices_labels(self):
        """ returns a list of strings that are the devices labels in the system """
        return self.do_request('get', '/devices/labels')

    def get_users_labels(self):
        """ returns a list of strings that are the users labels in the system """
        return self.do_request('get', '/users/labels')

    def add_labels(self, entities: list, labels: list):
        data = {
            'entities': entities,  # list of internal axon ids
            'labels': labels      # list of labels to add
        }
        return self.do_request('post', '/devices/labels', json=data)

    def delete_labels(self,  entities: list, labels: list):
        data = {
            'entities': entities,  # list of internal axon ids
            'labels': labels       # list of labels to add
        }
        return self.do_request('delete', '/devices/labels', json=data)


class RESTExample:
    def __init__(self, axonius_url, username,
                 password, verify_ssl):
        self._client = RESTClient(axonius_url,
                                  username,
                                  password,
                                  verify=verify_ssl)

    @classmethod
    def get_examples(cls):
        examples_functions = (cls.get_devices1,
                              cls.get_devices2,
                              cls.get_device_by_id,
                              cls.get_devices_views,
                              cls.create_new_device_view,
                              cls.delete_device_view,
                              cls.get_users,
                              cls.get_user_by_id,
                              cls.get_users_view,
                              cls.save_users_view,
                              cls.delete_user_view,
                              cls.get_alerts,
                              cls.delete_alert,
                              cls.put_alert,
                              cls.get_actions,
                              cls.deploy_action,
                              cls.shell_action,
                              cls.get_users_labels,
                              cls.get_devices_labels,
                              cls.add_labels,
                              cls.delete_labels)
        return [function.__name__ for function in examples_functions]

    def get_devices1(self):
        params = {}

        # These paramters are REQUIRED. This will get first 50 devices.
        return self._client.get_devices(skip=70, limit=50)
        # The request would look like this
        # https://localhost/api/V1/devices?limit=50&skip=170

        # This would query a max of 50 devices with no filters on either the devices themselves or their fields
        # and will skip the first 170 devices.

    def get_devices2(self):
        params = {}

        # These paramters are REQUIRED. This will get first 50 devices.
        params['skip'] = 0
        params['limit'] = 50

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
        return self._client.get_devices(skip=0, limit=50, fields=fields, filter_=filter_)

    def get_device_by_id(self):
        return self._client.get_device_by_id(device_id='8b45e72e83a1451785630501bdcda95b')

    def get_devices_views(self):
        # https://localhost/api/devices/views?limit=1000&skip=0&filter=query_type==%27saved%27
        return self._client.get_devices_views(skip=0, limit=1000, filter_='query_type==\'saved\'')

    def create_new_device_view(self):
        name = 'All Nexpose Scanned AD Devices'
        view = {'page': 0,
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
        query_type = 'saved'

        # Creates a new saved query named: "All Nexpose Scanned AD Devices" That gets all the devices that have been
        # queried from both Rapid 7 Nexpose and Active Directory
        return self._client.create_new_device_view(name, view, query_type)

    def delete_device_view(self):
        raise NotImplementedError()

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

        return self._client.get_users(skip, limit, fields, filter_)

    def get_user_by_id(self):
        raise NotImplementedError()

    def get_users_view(self):
        # https://localhost/api/users/views?limit=1000&skip=0&filter=query_type==%27saved%27
        return self._client.get_users_view(0, 1000, 'query_type==\'saved\'')

    def save_users_view(self):
        name = 'Not Local Users'
        view = {'page': 0, 'pageSize': 20,
                'fields': ['specific_data.data.image',
                           'specific_data.data.username',
                           'specific_data.data.domain',
                           'specific_data.data.last_seen',
                           'specific_data.data.is_admin',
                           'specific_data.data.last_seen_in_devices'],
                'coloumnSizes': [],
                'query': {'filter': 'specific_data.data.is_local == True',
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
        query_type = 'saved'

        return self._client.save_users_view(name, view, query_type)

    def delete_user_view(self):
        raise NotImplementedError()

    def get_alerts(self):
        # https://localhost/api/alert?skip=NaN&limit=0&fields=name,report_creation_time,triggered,view,severity
        fields = ['name', 'report_creation_time', 'triggered', 'view', 'severity']
        return self._client.get_alerts(fields=','.join(fields))

    def delete_alert(self):
        raise NotImplementedError()

    def put_alert(self):
        trigger_dict = TRIGGERS_DEFAULT_VALUES
        trigger_dict['above'] = 1
        self._client.put_alert(name='Test Alert',
                               triggers=trigger_dict,
                               period='weekly',
                               actions=[{'type': 'create_notification'}],
                               view='Users Created in Last 30 Days',
                               viewEntity='users',
                               severity='warning')

    def get_actions(self):
        return self._client.get_actions()

    def shell_action(self):
        return self._client.shell_action(device_ids=['device_id'],  # The device
                                         action_name=ACTION_PUT_FILE,
                                         command=PUT_FILE_EXAMPLE)

    def deploy_action(self):
        return self._client.deploy_action(device_ids=['device_id'],  # The device
                                          action_name=ACTION_RUN_SCRIPT,
                                          binary=RUN_SCRIPT_EXAMPLE)

    def get_devices_labels(self):
        return self._client.get_devices_labels()

    def get_users_labels(self):
        return self._client.get_devices_labels()

    def add_labels(self):
        entities = ['internal_axon_id1', 'internal_axon_id2']
        labels = ['labels to add', 'another label']
        return self._client.add_labels(entities, labels)

    def delete_labels(self):
        entities = ['internal_axon_id1', 'internal_axon_id2']
        labels = ['labels to add', 'another label']
        return self._client.delete_labels(entities, labels)


def main():
    requests.packages.urllib3.disable_warnings()
    logging.basicConfig(format='%(message)s', level=logging.INFO)

    args = ArgumentParser().parse_args()

    client = RESTExample(args.axonius_url,
                         args.username,
                         args.password,
                         not args.no_verify_ssl)
    if args.function:
        print(f'Calling api function "{args.function}"')
        callback = getattr(client, args.function)
        callback()

    if args.all_functions:
        for name in client.get_examples():
            try:
                print(f'Calling api function "{name}"')
                callback = getattr(client, name)
                callback()
                print('\n\n')
            except NotImplementedError:
                continue


if __name__ == '__main__':
    main()
