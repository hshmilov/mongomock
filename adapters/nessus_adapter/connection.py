import logging
logger = logging.getLogger(f"axonius.{__name__}")
import requests

from nessus_adapter.exceptions import NessusNotConnected, NessusAlreadyConnected, NessusCredentialMissing, \
    NessusConnectionError, NessusRequestError

DEFAULT_NESSUS_PORT = 8834
TOKEN = 'token'
SESSION = 'session'
HTTP_PREFIX = 'https://'
USERNAME = 'username'
PASSWORD = 'password'

SCANS_ENDPOINT = "scans"
SCAN_DETAILS_ENDPOINT = "scans/{0}"
HOSTS_PARAM = "hosts"
HOST_DETAILS_ENDPOINT = "scans/{0}/hosts/{1}"


class NessusConnection(object):
    def __init__(self, host, port, verify_ssl):
        self.username = None
        self.password = None
        self.access_key = None
        self.secret_key = None
        self.token = None
        self.should_use_token = True  # Setting a default of true
        self.host = host
        self.port = port if port is not None else DEFAULT_NESSUS_PORT
        self.url = host + ':' + str(self.port)
        if not self.url.lower().startswith(HTTP_PREFIX):
            self.url = HTTP_PREFIX + self.url
        if not self.url.endswith('/'):
            self.url += '/'
        self.session = None
        self.verify_ssl = verify_ssl
        self.headers = {'Content-Type': 'application/json'}

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.disconnect()

    def __del__(self):
        if hasattr(self, SESSION) and self._is_connected and self.should_use_token:
            try:
                self.disconnect()
            except Exception:
                pass
            self._close()

    @property
    def _is_connected(self):
        return self.session is not None

    def set_credentials(self, username=None, password=None, api_access_key=None, api_secret_key=None):
        """
        :param username:
        :param password:
        :param api_access_key:
        :param api_secret_key:
        :return:
        """
        if username is not None and username != "" and password is not None and password != "":
            # We should use the user and password
            self.should_use_token = True
            self.username = username
            self.password = password
        elif api_access_key is not None and api_access_key != "" and \
                api_secret_key is not None and api_secret_key != "":
            # We should just use the given api keys
            self.should_use_token = False
            self.access_key = api_access_key
            self.secret_key = api_secret_key
        else:
            raise NessusCredentialMissing("Missing user/password or api keys")

    def connect(self):
        """
        Request a connection session with saved credentials
        Save returned token for performing requests, since they require authorization

        """
        if self._is_connected and self.should_use_token:
            raise NessusAlreadyConnected()
        if self.should_use_token:
            # This code will generate token and create session if user entered user/password
            session = requests.Session()
            if (self.username is None or self.password is None) and self.token is None:
                raise NessusCredentialMissing()
            elif self.username is None or self.password is None:
                return

            try:
                response = session.post(self._get_url_request(SESSION), headers=self.headers,
                                        json={USERNAME: self.username, PASSWORD: self.password},
                                        verify=self.verify_ssl, timeout=(5, 30))
                response.raise_for_status()
            except requests.HTTPError as e:
                raise NessusConnectionError(
                    "POST /session with username {0} failed. Details: {1}".format(self.username, str(e)))
            response = response.json()
            if TOKEN not in response:
                error = response.get('errorCode', 'Unknown connection error')
                message = response.get('errorMessage', '')
                if message:
                    error = '{0}: {1}'.format(error, message)
                raise NessusConnectionError(error)
            self._set_token_headers(response[TOKEN])
            self.session = session
        else:
            # In this case we just need to set the headers of the api key
            self._set_api_headers()
            # Checking that the connection works
            self._get(SCANS_ENDPOINT)

    def get_scans(self, **kwargs):
        """
        Request scans from current Nessus connection

        :param kwargs
        :return: List of scans if exist, according to response
        """
        scans = self._get(SCANS_ENDPOINT, kwargs)
        if not scans or not scans.get(SCANS_ENDPOINT):
            logger.info("GET {0} returned no scans".format(SCANS_ENDPOINT))
            return []
        return scans[SCANS_ENDPOINT]

    def get_hosts(self, scan_id, **kwargs):
        """
        Request hosts of given scan from current Nessus connection

        :param scan_id: Id of the scan of which to fetch hosts
        :param kwargs: Override _get request parameters
        :return: List of hosts found by given scan
        """
        if not scan_id:
            logger.info("Missing required parameter for GET {0}".format(SCAN_DETAILS_ENDPOINT.format("<scan_id>")))
            return []
        hosts = self._get(SCAN_DETAILS_ENDPOINT.format(scan_id), kwargs)
        if not hosts or not hosts.get("hosts"):
            logger.info("GET {0} returned no hosts".format(SCAN_DETAILS_ENDPOINT.format(scan_id)))
            return []
        return hosts["hosts"]

    def get_host_details(self, scan_id, host_id, **kwargs):
        """
        Request host expanded details for given host in given scan

        :param scan_id: Id of the scan that resulted in requested host
        :param host_id: Id of the host to fetch
        :param open_session: An open requests session (increase performance)
        :param kwargs: Override _get request parameters
        :return: Expanded details of given host as found by given scan
        """
        if not scan_id or not host_id:
            logger.info(
                "Missing required parameter for GET {0}".format(HOST_DETAILS_ENDPOINT.format("<scan_id>", "<host_id")))
            return {}
        return self._get(HOST_DETAILS_ENDPOINT.format(scan_id, host_id), kwargs)

    def disconnect(self):
        """
        Destroy current session. to end the connection
        :return:
        """
        if self.should_use_token:
            response = self.session.delete(self._get_url_request(SESSION), headers=self.headers, verify=False)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise NessusRequestError("DELETE /session failed. Details: {0}".format(str(e)))
            self._close()
        return True

    def _close(self):
        """ Terminate the connection and initialize session and token """
        if self.should_use_token:
            self.session.close()
            self.session = None
            self.token = None

    def _get_url_request(self, endpoint):
        """ Builds and returns the full url for the request

        :param endpoint: path for requested endpoint
        :return: the full request url
        """
        return self.url + endpoint

    def _set_token_headers(self, token):
        """ Sets the API token, in the appropriate header, for valid requests

        :param str token: API Token
        """
        self.token = token
        self.headers['X-Cookie'] = 'token={0}'.format(token)

    def _set_api_headers(self):
        """ Setting headers to include the given api key
        """
        self.headers['X-ApiKeys'] = f'accessKey={self.access_key}; secretKey={self.secret_key}'

    def _get(self, name, params=None, headers=None, **kwargs):
        """
        Serves a GET request to Nessus API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :param dict headers: headers for the request
        :return: the response json
        :rtype: dict
        """
        open_session = kwargs.get("open_session")
        if not self._is_connected and self.should_use_token:
            raise NessusNotConnected()
        headers = headers if headers is not None else self.headers
        params = params if params is not None else {}
        if self.should_use_token:
            response = self.session.get(self._get_url_request(name), params=params,
                                        headers=headers, verify=self.verify_ssl, timeout=(5, 30))
        else:
            # Using api key instead of session with token
            if open_session is not None:
                response = open_session.get(self._get_url_request(name), params=params,
                                            headers=headers, verify=self.verify_ssl, timeout=(5, 30))
            else:
                response = requests.get(self._get_url_request(name), params=params,
                                        headers=headers, verify=self.verify_ssl, timeout=(5, 30))
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise NessusRequestError("GET {0} failed. Details: {1}".format(name, str(e)))
        return response.json()
