import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cherwell_adapter.consts import SERVERS_BUS_OB_ID

logger = logging.getLogger(f'axonius.{__name__}')


class CherwellConnection(RESTConnection):
    """ rest client for Cherwell adapter """

    def __init__(self, *args, client_id, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._client_id = client_id

    def _connect(self):
        if not self._username or not self._password or not self._client_id:
            raise RESTException('No username or password')
        response = self._post('token',
                              body_params={'grant_type': 'password',
                                           'client_id': self._client_id,
                                           'username': self._username,
                                           'password': self._password})

    def get_device_list(self):
        response = self._post('api/V1/getquicksearchresults',
                              body_params={'busObIds': [SERVERS_BUS_OB_ID],
                                           'searchText': ''})
        if not response or not isinstance(response, list):
            raise RESTException(f'Bad Response: {response}')
        for asset_raw in response:
            try:
                bus_ob_id = asset_raw.get('busObId')
                bus_ob_rec_id = asset_raw.get('busObRecId')
                if not bus_ob_id or not bus_ob_rec_id:
                    continue
                asset_response = self._post('api/V1/getbusinessobjectbatch',
                                            body_params={'readRequests': [{'busObId': bus_ob_id,
                                                                           'busObPublicId': '',
                                                                           'busObRecId': bus_ob_rec_id}],
                                                         'stopOnError': True})
                yield asset_response, bus_ob_id, bus_ob_rec_id
            except Exception:
                logger.exception(f'Problem with asset: {asset_raw}')
