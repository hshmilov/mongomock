import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from bluecat_adapter.consts import DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class BluecatConnection(RESTConnection):
    """ rest client for Bluecat adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='Services/REST/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)

    def _refresh_token(self):
        try:
            response = self._get(f'login?username={self._username}&password={self._password}',
                                 use_json_in_response=False)
        except Exception:
            logger.exception('Authentication Error')
            raise RESTException('Authentication Error')
        response = str(response)
        if 'ERROR' in response:
            raise RESTException('Bad Authentication')
        if '->' not in response or '<-' not in response:
            raise RESTException(f'Bad Response for login: {response}')
        index_start = response.index('->') + len('->')
        index_end = response.index('<-')
        if index_end <= index_start:
            raise RESTException(f'Got Empty Token: {response}')
        token = response[index_start:index_end].strip()
        if not token:
            raise RESTException(f'Got Empty Token: {response}')
        self._session_headers['Authorization'] = token
        self._token_time = datetime.datetime.now()

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._refresh_token()

    # pylint: disable=R0912
    def get_device_list(self):
        networks_ids = set()
        for key_num in range(1, 256):
            try:
                response = self._get(f'searchByObjectTypes?'
                                     f'keyword={key_num}$&types=IP4Network&start=0&'
                                     f'count={DEVICE_PER_PAGE}')
                for network_raw in response:
                    if network_raw.get('id'):
                        networks_ids.add(network_raw.get('id'))
            except Exception:
                logger.exception(f'Problem getting key num')
        if (datetime.datetime.now() - self._token_time) > datetime.timedelta(minutes=5):
            self._refresh_token()
        # pylint: disable=R1702
        networks_ids = list(networks_ids)
        for network_id in networks_ids:
            try:
                if (datetime.datetime.now() - self._token_time) > datetime.timedelta(minutes=5):
                    self._refresh_token()
                response = self._get(f'getEntities?parentId={network_id}&type=IP4Address'
                                     f'&start=0&count={DEVICE_PER_PAGE}')
                for device_raw in response:
                    try:
                        host_id = device_raw.get('id')
                        if host_id:
                            if (datetime.datetime.now() - self._token_time) > datetime.timedelta(minutes=5):
                                self._refresh_token()
                            dns_name_raw = self._get(f'getLinkedEntities?entityId={host_id}&type=HostRecord&'
                                                     f'start=0&count={DEVICE_PER_PAGE}')
                            if isinstance(dns_name_raw, list) and len(dns_name_raw) > 0:
                                device_raw['dns_name'] = dns_name_raw[0].get('name')
                    except Exception:
                        logger.exception(f'Problem getting dns name for {device_raw}')
                    yield device_raw
            except Exception:
                logger.exception(f'Problem getting network id {network_id}')
