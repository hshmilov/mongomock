import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cherwell_adapter.consts import SERVERS_BUS_OB_ID

logger = logging.getLogger(f'axonius.{__name__}')


class CherwellConnection(RESTConnection):
    """ rest client for Cherwell adapter """

    def __init__(self, *args, client_id, **kwargs):
        super().__init__(*args, url_base_prefix='CherwellAPI',
                         headers={'Accept': 'application/json'},
                         **kwargs)
        self._client_id = client_id
        self._last_refresh = None
        self._expires_in = None

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        response = self._post('token',
                              use_json_in_body=False,
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              body_params={'grant_type': 'password',
                                           'client_id': self._client_id,
                                           'username': self._username,
                                           'password': self._password})
        if not isinstance(response, dict) or 'access_token' not in response:
            raise RESTException(f'Bad response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in'])

    def _connect(self):
        if not self._username or not self._password or not self._client_id:
            raise RESTException('No username or password or not Client ID')
        self._refresh_token()
        self._last_refresh = None
        self._expires_in = None

    def get_device_list(self):
        self._refresh_token()
        response = self._post('api/V1/getquicksearchresults',
                              body_params={'busObIds': [SERVERS_BUS_OB_ID],
                                           'searchText': ''})
        if not response or not isinstance(response, dict) or not isinstance(response.get('groups'), list):
            raise RESTException(f'Bad Response: {response}')
        num_groups = len(response['groups'])
        logger.info(f'Number of groups is {num_groups}')
        for group_raw in response['groups']:
            try:
                if not group_raw.get('simpleResultsListItems')\
                        or not isinstance(group_raw.get('simpleResultsListItems'), list):
                    continue
                num_assets = len(group_raw.get('simpleResultsListItems'))
                logger.info(f'Number of asset in this group is {num_assets}')
                for asset_raw in group_raw.get('simpleResultsListItems'):
                    try:
                        bus_ob_id = asset_raw.get('busObId')
                        bus_ob_rec_id = asset_raw.get('busObRecId')
                        if not bus_ob_id or not bus_ob_rec_id:
                            continue
                        self._refresh_token()
                        asset_response = self._post('api/V1/getbusinessobjectbatch',
                                                    body_params={'readRequests': [{'busObId': bus_ob_id,
                                                                                   'busObPublicId': '',
                                                                                   'busObRecId': bus_ob_rec_id}],
                                                                 'stopOnError': True})
                        yield asset_response
                    except Exception:
                        logger.exception(f'Problem with asset: {asset_raw}')
            except Exception:
                logger.exception(f'Problem with group raw {group_raw}')
