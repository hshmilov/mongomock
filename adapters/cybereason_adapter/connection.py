import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cybereason_adapter.consts import DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class CybereasonConnection(RESTConnection):
    """ rest client for Cybereason adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='rest',
                         headers={'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if self._username and self._password:
            self._post('login.html', use_json_in_body=False, use_json_in_response=False,
                       body_params={'username': self._username,
                                    'password': self._password})
        else:
            raise RESTException('No username or password')

    def get_device_list(self):
        self._session_headers['Content-Type'] = 'application/json'
        query = '{"filters":[{"fieldName":"status","operator":"NotEquals","values":["Archived"]}],' \
                '"sortingFieldName":"machineName","sortDirection":"ASC","limit":' + \
                str(DEVICE_PER_PAGE) + ',"offset":' + str(0) + ',"batchId":null}'
        response = self._post('sensors/query', use_json_in_body=False, body_params=query)
        total_count = response['totalResults']
        query = '{"filters":[{"fieldName":"status","operator":"NotEquals","values":["Archived"]}],' \
                '"sortingFieldName":"machineName","sortDirection":"ASC","limit":' + \
                str(total_count) + ',"offset":' + str(0) + ',"batchId":null}'
        response = self._post('sensors/query', use_json_in_body=False, body_params=query)
        # I know we might yield devices again, But due to this problematic API I kept it this way (ofri)
        yield from response['sensors']

    def update_isolate_status(self, pylum_id, malop_id, do_isolate):
        if not do_isolate:
            command_url = 'monitor/global/commands/un-isolate'
        else:
            command_url = 'monitor/global/commands/isolate'
        command_dict = {'pylumIds': [pylum_id], 'malopId': malop_id}
        self._post(command_url, body_params=command_dict)
        query = '{"filters":[{"fieldName":"status","operator":"NotEquals","values":["Archived"]},' \
                '{"fieldName":"status","operator":"Equals","values":["' + str(pylum_id) + '"]}],' \
                '"sortingFieldName":"machineName","sortDirection":"ASC","limit":' + \
                str(1) + ',"offset":' + str(0) + ',"batchId":null}'
        response = self._post('sensors/query', use_json_in_body=False, body_params=query)
        if response.get('sensors'):
            return response['sensors'][0]
        return None
