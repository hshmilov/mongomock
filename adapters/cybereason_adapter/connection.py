import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cybereason_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class CybereasonConnection(RESTConnection):
    """ rest client for Cybereason adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if self._username and self._password:
            self._post('login.html', use_json_in_body=False,
                       body_params={'username': self._username,
                                    'password': self._password})
        else:
            raise RESTException('No username or password')

    def get_device_list(self):
        self._session_headers['Content-Type'] = 'application/json'
        query = '{"filters":[{"fieldName":"status","operator":"NotEquals","values":["Archived"]}],' \
                '"sortingFieldName":"machineName","sortDirection":"ASC","limit":' + \
                str(DEVICE_PER_PAGE) + ',"offset":' + str(0) + ',"batchId":null}'
        response = self._post('rest/sensors/query', use_json_in_body=False, body_params=query)
        yield from response['sensors']
        total_count = response['totalResults']
        offset = DEVICE_PER_PAGE
        while offset < min(total_count, MAX_NUMBER_OF_DEVICES):
            try:
                query = '{"filters":[{"fieldName":"status","operator":"NotEquals","values":["Archived"]}],' \
                        '"sortingFieldName":"machineName","sortDirection":"ASC","limit":' + \
                        str(DEVICE_PER_PAGE) + ',"offset":' + str(offset) + ',"batchId":null}'
                response = self._post('rest/sensors/query', use_json_in_body=False, body_params=query)
                yield from response['sensors']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem with offset {offset}')
                break
