import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class SignalsciencesConnection(RESTConnection):
    """ rest client for Signalsciences adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v0',
                         headers={'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('auth',
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              use_json_in_body=False,
                              body_params={'email': self._username,
                                           'password': self._password})
        if not response.get('token'):
            raise RESTException(f'Bad Token Response: {response}')
        self._token = response['token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        corps_raw = self._get('corps')
        if 'data' not in corps_raw or not corps_raw.get('data'):
            raise RESTException(f'Bad Corps Response: {corps_raw}')

    def get_device_list(self):
        corp_names = []
        for corp_raw in self._get('corps')['data']:
            if isinstance(corp_raw, dict) and corp_raw.get('name'):
                corp_names.append(corp_raw.get('name'))
        corps_sites_dict = dict()
        for corp_name in corp_names:
            try:
                corps_sites_dict[corp_name] = []
                for site_raw in self._get(f'corps/{corp_name}/sites')['data']:
                    if isinstance(site_raw, dict) and site_raw.get('name'):
                        corps_sites_dict[corp_name].append(site_raw.get('name'))
            except Exception:
                logger.exception(f'Problem getting sites for {corp_name}')
        for corp_name, site_names in corps_sites_dict.items():
            try:
                for site_name in site_names:
                    try:
                        yield from self._get(f'corps/{corp_name}/sites/{site_name}/agents')['data']
                    except Exception:
                        logger.exception(f'Problem getting agents for {corp_name} with specific site {site_name}')
            except Exception:
                logger.exception(f'Problem getting agents for {corp_name} with sites {site_names}')
