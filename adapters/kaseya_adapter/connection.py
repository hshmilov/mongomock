import logging
import random
import hashlib
import base64
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection
from kaseya_adapter import consts


class KaseyaConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(url_base_prefix='api/v1.0/', *args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def __generate_auth(self):
        rand_number = random.randrange(100)

        sha256_instance = hashlib.sha256()
        sha256_instance.update(self._password.encode("utf-8"))
        raw_SHA256_hash = sha256_instance.hexdigest()

        sha256_instance = hashlib.sha256()
        sha256_instance.update((self._password + self._username).encode("utf-8"))
        covered_SHA256_hash_temp = sha256_instance.hexdigest()

        sha256_instance = hashlib.sha256()
        sha256_instance.update((covered_SHA256_hash_temp + str(rand_number)).encode("utf-8"))
        covered_SHA256_hash = sha256_instance.hexdigest()

        sha1_instance = hashlib.sha1()
        sha1_instance.update(self._password.encode("utf-8"))
        raw_SHA1_hash = sha1_instance.hexdigest()

        sha1_instance = hashlib.sha1()
        sha1_instance.update((self._password + self._username).encode("utf-8"))
        covered_SHA1_hash_temp = sha1_instance.hexdigest()

        sha1_instance = hashlib.sha1()
        sha1_instance.update((covered_SHA1_hash_temp + str(rand_number)).encode("utf-8"))
        covered_SHA1_hash = sha1_instance.hexdigest()

        auth_string = "user=" + self._username + "," + "pass2=" + covered_SHA256_hash + "," +\
                      "pass1=" + covered_SHA1_hash + "," + "rpass2=" + raw_SHA256_hash + "," +\
                      "rpass1=" + raw_SHA1_hash + "," + "rand2=" + str(rand_number)
        return base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    def _connect(self):
        if self._username is not None and self._password is not None:
            self._session_headers['Authorization'] = "Basic " + self.__generate_auth()
            response = self._get('auth')
            self._session_headers['Authorization'] = "Bearer " + response["Result"]["Token"]
        else:
            raise RESTException("No user name or password")

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Kaseya's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        # Becuase we have two important list: Agents and Assets,
        # we have to get at list all the agents list in memory and then yield only on assets list
        total_agents_records = self._get('assetmgmt/agents', url_params={'$top': 1})["TotalRecords"]
        agents_raw = []
        skip = 0
        while skip < total_agents_records and skip < consts.MAX_DEVICES:
            try:
                agents_raw += self._get('assetmgmt/agents',
                                        url_params={'$top': consts.DEVICES_PER_PAGE,
                                                    '$skip': skip})["Result"]

            except Exception:
                logger.exception(f"Got problem fetching agents in offset {skip}")
            skip += consts.DEVICES_PER_PAGE
        agents_id_dict = dict()
        for agent_raw in agents_raw:
            try:
                agents_id_dict[agent_raw['AgentId']] = agent_raw
            except Exception:
                logger.exception(f"Problem getting ID for agent {agent_raw}")

        total_assets_records = self._get('assetmgmt/assets', url_params={'$top': 1})["TotalRecords"]
        skip = 0
        while skip < total_assets_records and skip < consts.MAX_DEVICES:
            try:
                assets_raw = self._get('assetmgmt/assets',
                                       url_params={'$top': consts.DEVICES_PER_PAGE,
                                                   '$skip': skip}
                                       )["Result"]
                for asset_raw in assets_raw:
                    yield asset_raw, agents_id_dict
            except Exception:
                logger.exception(f"Got problem fetching assets in offset {skip}")
            skip += consts.DEVICES_PER_PAGE
