import requests
import logging
import random
import hashlib
import base64
logger = logging.getLogger(f'axonius.{__name__}')

from kaseya_adapter.exceptions import KaseyaAlreadyConnected, KaseyaConnectionError, KaseyaNotConnected, \
    KaseyaRequestException


class KaseyaConnection(object):
    def __init__(self, domain, verify_ssl):
        """ Initializes a connection to Kaseya using its rest API

        :param str domain: domain address for Kaseya
        :param bool verify_ssl Verify the ssl
        """
        self.domain = domain
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        if not url.endswith('/'):
            url += '/'
        url += 'api/v1.0/'
        self.url = url
        self.session = None
        self.username = None
        self.password = None
        self.verify_ssl = verify_ssl
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def set_credentials(self, username, password):
        """ Set the connection credentials

        :param str username: The username
        :param str password: The password
        """
        self.username = username
        self.password = password

    def _get_url_request(self, request_name):
        """ Builds and returns the full url for the request

        :param request_name: the request name
        :return: the full request url
        """
        return self.url + request_name

    @property
    def is_connected(self):
        return self.session is not None

    def generate_auth(self):
        rand_number = random.randrange(100)

        sha256_instance = hashlib.sha256()
        sha256_instance.update(self.password.encode("utf-8"))
        raw_SHA256_hash = sha256_instance.hexdigest()

        sha256_instance = hashlib.sha256()
        sha256_instance.update((self.password + self.username).encode("utf-8"))
        covered_SHA256_hash_temp = sha256_instance.hexdigest()

        sha256_instance = hashlib.sha256()
        sha256_instance.update((covered_SHA256_hash_temp + str(rand_number)).encode("utf-8"))
        covered_SHA256_hash = sha256_instance.hexdigest()

        sha1_instance = hashlib.sha1()
        sha1_instance.update(self.password.encode("utf-8"))
        raw_SHA1_hash = sha1_instance.hexdigest()

        sha1_instance = hashlib.sha1()
        sha1_instance.update((self.password + self.username).encode("utf-8"))
        covered_SHA1_hash_temp = sha1_instance.hexdigest()

        sha1_instance = hashlib.sha1()
        sha1_instance.update((covered_SHA1_hash_temp + str(rand_number)).encode("utf-8"))
        covered_SHA1_hash = sha1_instance.hexdigest()

        auth_string = "user=" + self.username + "," + "pass2=" + covered_SHA256_hash + "," +\
                      "pass1=" + covered_SHA1_hash + "," + "rpass2=" + raw_SHA256_hash + "," +\
                      "rpass1=" + raw_SHA1_hash + "," + "rand2=" + str(rand_number)
        return base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    def connect(self):
        """ Connects to the service """
        if self.is_connected:
            raise KaseyaAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            self.headers['Authorization'] = "Basic " + self.generate_auth()
            try:
                response = session.get(self._get_url_request('auth'), headers=self.headers,
                                       verify=self.verify_ssl, timeout=(5, 30))
                response.raise_for_status()
                self.headers['Authorization'] = "Bearer " + response.json()["Result"]["Token"]
                logger.debug(f"Got this auth response {response.text}")
            except requests.HTTPError as e:
                raise KaseyaConnectionError(str(e))
        else:
            raise KaseyaConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _post(self, name, params=None):
        """ Serves a POST request to Kaseya API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise KaseyaNotConnected()
        params = params or {}
        try:
            response = self.session.post(self._get_url_request(name), json=params,
                                         headers=self.headers, verify=self.verify_ssl, timeout=(5, 30))
            response.raise_for_status()
        except requests.HTTPError as e:
            raise KaseyaRequestException(str(e))
        return response.json()

    def _get(self, name, params=None):
        """ Serves a GET request to Kaseya API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise KaseyaNotConnected()
        params = params or {}
        try:
            response = self.session.get(self._get_url_request(name), params=params,
                                        headers=self.headers, verify=self.verify_ssl, timeout=(5, 30))
            response.raise_for_status()
        except requests.HTTPError as e:
            raise KaseyaRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Kaseya's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        total_records = self._get('assetmgmt/agents?$top=1')["TotalRecords"]
        agents_raw = []
        assets_raw = []
        top = 100
        skip = 0
        while skip < total_records:
            try:
                agents_raw += self._get('assetmgmt/agents?$top=' + str(top) + '&$skip=' + str(skip))["Result"]
                skip += top
            except Exception:
                logger.exception(f"Got problem fetching agents in offset {skip}")
        top = 100
        skip = 0
        while skip < total_records:
            try:
                assets_raw += self._get('assetmgmt/assets?$top=' + str(top) + '&$skip=' + str(skip))["Result"]
                skip += top
            except Exception:
                logger.exception(f"Got problem fetching assets in offset {skip}")

        agents_id_dict = dict()
        for agent_raw in agents_raw:
            try:
                agents_id_dict[agent_raw['AgentId']] = agent_raw
            except Exception:
                logger.exception(f"Problem getting ID for agent {agent_raw}")
        return {'agents': agents_id_dict, 'assets': assets_raw}

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
