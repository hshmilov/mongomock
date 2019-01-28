import logging
import pprint
import typing
import urllib3

import requests

# pylint: disable=too-many-arguments,too-many-public-methods

# Suppress InsecureRequestWarning: Unverified HTTPS request
urllib3.disable_warnings()

AXONIUS_API = '/api/V1'


class RESTClient:
    """ simple rest client for Axonius REST API """

    def __init__(self, axonius_url, **kwargs):
        self._url = axonius_url
        self._request_args = kwargs
        self._logger = logging.getLogger('RESTClient')

    def do_request(self, action: str, url: str, **kwargs):
        """ Sends axnoius rest api to the server """
        kwargs.update(self._request_args)

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

    def get_devices(self, skip: int, limit: int, fields: str = None, filter_: str = None):
        params = {}
        params['skip'] = skip
        params['limit'] = limit

        if fields:
            params['fields'] = fields
        if filter_:
            params['filter'] = filter_

        return self.do_request('get', '/devices', params=params)

    def get_devices_count(self, filter_: str = None):
        params = {}
        if filter_:
            params['filter'] = filter_

        return self.do_request('get', '/devices/count', params=params)

    def get_device_by_id(self, device_id: str):
        return self.do_request('get', f'/devices/{device_id}')

    def get_devices_views(self, skip: int, limit: int, filter_: str):
        params = {}
        params['limit'] = limit
        params['skip'] = skip
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

    def get_users_count(self, filter_: str = None):
        params = {}
        if filter_:
            params['filter'] = filter_

        return self.do_request('get', '/users/count', params=params)

    def get_user_by_id(self, user_id: str):
        return self.do_request('get', f'/users/{user_id}')

    def get_users_views(self, skip: str, limit: str, filter_: list = None):

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

    def get_alerts(self, skip: int = None, limit: int = None, fields: list = None):
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
                  view_entity: str,
                  severity: str,
                  retrigger: bool = True,
                  triggered: bool = False):
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
                'viewEntity': view_entity,
                'retrigger': retrigger,
                'triggered': triggered,
                'severity': severity}

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
                      params: str = ''):
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

    def add_devices_labels(self, entities: list, labels: list):
        data = {
            'entities': {
                'ids': entities,  # list of internal axon ids
            },
            'labels': labels      # list of labels to add
        }
        return self.do_request('post', '/devices/labels', json=data)

    def delete_devices_labels(self, entities: list, labels: list):
        data = {
            'entities': {
                'ids': entities,
            },                     # list of internal axon ids
            'labels': labels       # list of labels to add
        }
        return self.do_request('delete', '/devices/labels', json=data)

    def add_users_labels(self, entities: list, labels: list):
        data = {
            'entities': {
                'ids': entities,  # list of internal axon ids
            },
            'labels': labels      # list of labels to add
        }
        return self.do_request('post', '/users/labels', json=data)

    def delete_users_labels(self, entities: list, labels: list):
        data = {
            'entities': {
                'ids': entities,
            },                     # list of internal axon ids
            'labels': labels       # list of labels to add
        }
        return self.do_request('delete', '/users/labels', json=data)

    def upload_file(self, binary: typing.io.BinaryIO):
        """ Upload a file to the system, that later can be use for deployment """
        return self.do_request('post', '/actions/upload_file', data={'field_name': 'binary'},
                               files={'userfile': ('example_filename', binary)})

    def get_adapters(self):
        return self.do_request('get', '/adapters')

    def check_connectivity(self, adapter_name: str, client_config: dict, node_id: str):
        data = {}

        data.update(client_config)

        data.update({'instanceName': node_id,
                     'oldInstanceName': node_id})

        return self.do_request('post', f'/adapters/{adapter_name}/clients', json=data)

    def add_client(self, adapter_name: str, client_config: dict, node_id: str):
        data = {}

        data.update(client_config)
        data.update({'instanceName': node_id})
        return self.do_request('put', f'/adapters/{adapter_name}/clients', json=data)

    def delete_client(self, adapter_name: str, client_id: str, node_id: str):
        data = {'instanceName': node_id}
        return self.do_request('delete', f'/adapters/{adapter_name}/clients/{client_id}', json=data)
