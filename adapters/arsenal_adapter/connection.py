import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from arsenal_adapter.consts import DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class ArsenalConnection(RESTConnection):
    """ rest client for Arsenal adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={
                             'RPC-Service': 'arsenal',
                             'RPC-Procedure': 'uber.engsec.arsenal.Arsenal::Search',
                             'RPC-Caller': 'my-service-name',
                             'RPC-Encoding': 'json',
                             'Context-TTL-MS': '20000'},
                         **kwargs)

    def _connect(self):
        response = self._post('', body_params={'page': {'size': DEVICE_PER_PAGE}}, return_response_raw=True)
        error_header = response.headers.get('Grpc-Status-Details-Bin')
        json_data = response.json()
        if error_header is not None:
            raise RESTException(f'Got Error: {error_header}')
        if not json_data.get('assets'):
            raise RESTException(f'Bad response data: {json_data}')

    def get_device_list(self):
        response = self._post('', body_params={'page': {'size': DEVICE_PER_PAGE}}, return_response_raw=True)
        json_data = response.json()
        error_header = response.headers.get('Grpc-Status-Details-Bin')
        if error_header is not None:
            raise RESTException(f'Got Error: {error_header}')
        if not json_data.get('assets'):
            raise RESTException(f'Bad response data: {json_data}')
        yield from json_data['assets']
        token = json_data['page']['token']
        while token:
            try:
                response = self._post('', body_params={'page': {'size': DEVICE_PER_PAGE, 'token': token}},
                                      return_response_raw=True)
                json_data = response.json()
                error_header = response.headers.get('Grpc-Status-Details-Bin')
                if error_header is not None:
                    raise RESTException(f'Got Error: {error_header}')
                if not json_data.get('assets'):
                    raise RESTException(f'Bad response data: {json_data}')
                yield from json_data['assets']
                token = json_data['page']['token']
            except Exception:
                logger.exception(f'Problem with fetch')
                break
