import logging
from typing import Optional, List

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
                             'RPC-Caller': 'axonius-adapter',
                             'RPC-Encoding': 'json',
                             'Context-TTL-MS': '20000'},
                         **kwargs)

    def _connect(self):
        response = self._post('', body_params={'page': {'size': DEVICE_PER_PAGE}}, return_response_raw=True,
                              use_json_in_response=False)
        error_header = response.headers.get('Grpc-Status-Details-Bin')
        json_data = response.json()
        if error_header is not None:
            raise RESTException(f'Got Error: {error_header}')
        if not json_data.get('assets'):
            raise RESTException(f'Bad response data: {json_data}')

    # pylint: disable=arguments-differ
    def get_device_list(self, asset_types: Optional[List[str]], asset_statuses: Optional[List[str]]):
        query = {'page': {'size': DEVICE_PER_PAGE}}
        if asset_types:
            query['asset_types'] = asset_types
        if asset_statuses:
            query['asset_statuses'] = asset_statuses
        response = self._post('', body_params=query, return_response_raw=True,
                              use_json_in_response=False)
        json_data = response.json()
        error_header = response.headers.get('Grpc-Status-Details-Bin')
        if error_header is not None:
            raise RESTException(f'Got Error: {error_header}')
        if not json_data.get('assets'):
            raise RESTException(f'Bad response data: {json_data}')
        yield from json_data['assets']
        token = json_data['page'].get('token')
        while token:
            query['page']['token'] = token
            try:
                response = self._post('', body_params=query, return_response_raw=True,
                                      use_json_in_response=False)
                json_data = response.json()
                error_header = response.headers.get('Grpc-Status-Details-Bin')
                if error_header is not None:
                    raise RESTException(f'Got Error: {error_header}')
                if not json_data.get('assets'):
                    raise RESTException(f'Bad response data: {json_data}')
                yield from json_data['assets']
                token = json_data['page'].get('token')
            except Exception:
                logger.exception(f'Problem with fetch')
                break
