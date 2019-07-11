import logging
import random
import hashlib
import base64

from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection
from kaseya_adapter.consts import DEVICES_PER_PAGE, MAX_DEVICES


logger = logging.getLogger(f'axonius.{__name__}')


class KaseyaConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='api/v1.0/',
                         headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                         **kwargs)

    def __generate_auth(self):
        rand_number = random.randrange(100)

        sha256_instance = hashlib.sha256()
        sha256_instance.update(self._password.encode('utf-8'))
        raw_SHA256_hash = sha256_instance.hexdigest()

        sha256_instance = hashlib.sha256()
        sha256_instance.update((self._password + self._username).encode('utf-8'))
        covered_SHA256_hash_temp = sha256_instance.hexdigest()

        sha256_instance = hashlib.sha256()
        sha256_instance.update((covered_SHA256_hash_temp + str(rand_number)).encode('utf-8'))
        covered_SHA256_hash = sha256_instance.hexdigest()

        sha1_instance = hashlib.sha1()
        sha1_instance.update(self._password.encode('utf-8'))
        raw_SHA1_hash = sha1_instance.hexdigest()

        sha1_instance = hashlib.sha1()
        sha1_instance.update((self._password + self._username).encode('utf-8'))
        covered_SHA1_hash_temp = sha1_instance.hexdigest()

        sha1_instance = hashlib.sha1()
        sha1_instance.update((covered_SHA1_hash_temp + str(rand_number)).encode('utf-8'))
        covered_SHA1_hash = sha1_instance.hexdigest()

        auth_string = 'user=' + self._username + ',' + 'pass2=' + covered_SHA256_hash + ',' +\
                      'pass1=' + covered_SHA1_hash + ',' + 'rpass2=' + raw_SHA256_hash + ',' +\
                      'rpass1=' + raw_SHA1_hash + ',' + 'rand2=' + str(rand_number)
        return base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No user name or password')
        self._session_headers['Authorization'] = 'Basic ' + self.__generate_auth()
        response = self._get('auth')
        if 'Result' not in response or 'Token' not in response['Result']:
            raise RESTException(f'Got bad auth response: {response}')
        self._session_headers['Authorization'] = 'Bearer ' + response['Result']['Token']
        self._get('assetmgmt/agents',
                  url_params={'$top': 1,
                              '$skip': 0})

    def _get_api_endpoint(self, endpoint):
        total_records = self._get(endpoint, url_params={'$top': 1})['TotalRecords']
        skip = 0
        while skip < min(total_records, MAX_DEVICES):
            try:
                yield from self._get(endpoint,
                                     url_params={'$top': DEVICES_PER_PAGE,
                                                 '$skip': skip})['Result']

            except Exception:
                # No break because we have
                logger.exception(f'Got problem fetching agents in offset {skip}')
            skip += DEVICES_PER_PAGE

    def get_device_list(self):
        # Becuase we have two important list: Agents and Assets,
        # we have to get at list all the agents list in memory and then yield only on assets list
        agents_raw = self._get_api_endpoint('assetmgmt/agents')
        agents_id_dict = dict()
        for agent_raw in agents_raw:
            try:
                if agent_raw.get('AgentId'):
                    agent_id = agent_raw.get('AgentId')
                    apps_raw = []
                    try:
                        apps_raw = list(self._get_api_endpoint(f'assetmgmt/'
                                                               f'audit/{agent_id}/software/installedapplications'))
                    except Exception:
                        logger.exception(f'Problem getting app for {agent_id}')
                    agent_raw['apps_raw'] = apps_raw
                    agents_id_dict[agent_id] = agent_raw
            except Exception:
                logger.exception(f'Problem getting ID for agent {agent_raw}')
        for asset_raw in self._get_api_endpoint('assetmgmt/assets'):
            yield asset_raw, agents_id_dict
