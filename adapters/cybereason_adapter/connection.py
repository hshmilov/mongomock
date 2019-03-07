import logging
from time import sleep

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cybereason_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_SLEEPS, TIME_TO_SLEEP

logger = logging.getLogger(f'axonius.{__name__}')


class CybereasonConnection(RESTConnection):
    """ rest client for Cybereason adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
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
        query_dict = {'filters': [{'fieldName': 'status',
                                   'operator': 'NotEquals',
                                   'values': ['Archived']
                                   }
                                  ],
                      'sortingFieldName': 'machineName',
                      'sortDirection': 'ASC',
                      'limit': DEVICE_PER_PAGE,
                      'offset': 0,
                      'batchId': None
                      }
        response = self._post('rest/sensors/query', body_params=query_dict)
        total_count = response['totalResults']
        query_dict['limit'] = total_count
        response = self._post('rest/sensors/query', body_params=query_dict)
        yield from response['sensors']

    def update_isolate_status(self, pylum_id, do_isolate):
        if not do_isolate:
            command_url = 'rest/monitor/global/commands/un-isolate'
        else:
            command_url = 'rest/monitor/global/commands/isolate'
        command_dict = {'pylumIds': [pylum_id]}
        self._post(command_url, body_params=command_dict)
        query_dict = {'filters': [{'fieldName': 'status',
                                   'operator': 'NotEquals',
                                   'values': ['Archived']
                                   },
                                  {'fieldName': 'pylumId',
                                   'operator': 'Equals',
                                   'values': [str(pylum_id)]
                                   }
                                  ],
                      'sortingFieldName': 'machineName',
                      'sortDirection': 'ASC',
                      'limit': 1,
                      'offset': 0,
                      'batchId': None
                      }
        number_of_sleeps = 0
        if do_isolate:
            isolate_word = 'isolate'
        else:
            isolate_word = 'unisolate'
        while number_of_sleeps < MAX_NUMBER_OF_SLEEPS:
            response = self._post('rest/sensors/query', body_params=query_dict)
            if response.get('sensors') and response['sensors'][0].get('isolated') == do_isolate:
                return response['sensors'][0]
            number_of_sleeps += 1
            sleep(TIME_TO_SLEEP)

        if number_of_sleeps == MAX_NUMBER_OF_SLEEPS:
            raise RESTException(f'Cant {isolate_word} device id {pylum_id}')
