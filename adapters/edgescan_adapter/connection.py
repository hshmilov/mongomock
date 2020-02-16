import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class EdgescanConnection(RESTConnection):
    """ rest client for Edgescan adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No API Key')
        response = self._get('hosts.json', do_basic_auth=True)
        if not isinstance(response, dict) or not response.get('hosts') or not isinstance(response['hosts'], list):
            raise RESTException(f'Bad Response: {response}')

    def get_device_list(self):
        response = self._get('hosts.json', do_basic_auth=True)
        if not isinstance(response, dict) or not response.get('hosts') or not isinstance(response['hosts'], list):
            raise RESTException(f'Bad Response: {response}')
        asset_id_names_dict = dict()
        try:
            for asset_raw in self._get('assets.json', do_basic_auth=True)['assets']:
                asset_id_names_dict[asset_raw.get('id')] = asset_raw.get('name')
        except Exception:
            logger.exception(f'Problem gettins asset names')
        for device_raw in response['hosts']:
            yield device_raw, asset_id_names_dict
