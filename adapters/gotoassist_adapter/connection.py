import requests

from gotoassist_adapter.exceptions import GotoassistAlreadyConnected, GotoassistConnectionError, GotoassistNotConnected, \
    GotoassistRequestException


class GotoassistConnection(object):
    def __init__(self, logger, domain):
        """ Initializes a connection to Gotoassist using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Gotoassist
        """
        self.logger = logger
        self.domain = domain
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url
        self.url = url
        self.session = None
        self.username = None
        self.password = None
        self.client_id = None
        self.client_secret = None
        self.gotoassist_code = None
        self.headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}

    def set_credentials(self, client_id, client_secret, username, password):
        """ Set the connection credentials

        :param str client_id: The client_id
        :param str client_secret: The client_secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
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

    def connect(self):
        """ Connects to the service """
        if self.is_connected:
            raise GotoassistAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None and self.client_id is not None and self.client_secret is not None:
            get_login_url = self.url + "/oauth/v2/authorize?response_type=code&client_id=" + self.client_id
            get_login_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'}
            response = requests.get(get_login_url, headers=get_login_headers)
            url_for_post = response.url
            data_params = {"emailAddress": self.username, "password": self.password, "submit": "Sign in",
                           "_eventId": "submit", "lt": "", "execution": ""}
            login_headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                             'Content-Type': 'application/x-www-form-urlencoded'}
            response = requests.post(url_for_post,
                                     headers=login_headers, data=data_params)
            # To understand this code please check "https://goto-developer.logmeininc.com/how-get-access-token-and-organizer-key"
            # From this page: "IMPORTANT: You may see an error on the page such as 404 NOT FOUND. This is not a problem."
            if response.status_code != 404:
                raise GotoassistConnectionError(f"Couldn't get code. Status code is {response.status_code}")
            self.gotoassist_code = response.url.split('=')[-1]
        else:
            raise GotoassistConnectionError("Missing arguement")
        if self.gotoassist_code is not None:
            response = session.post(self._get_url_request('/oauth/v2/token'), auth=(self.client_id, self.client_secret),
                                    data={'grant_type': 'authorization_code', 'code': self.gotoassist_code},
                                    headers=self.headers)
            try:
                response.raise_for_status()
                self.headers['Authorization'] = "OAuth oauth_token=" + str(response.json()["access_token"])
            except requests.HTTPError as e:
                raise GotoassistConnectionError(str(e))
        else:
            raise GotoassistConnectionError("Couldn't get code")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _post(self, name, params=None):
        """ Serves a POST request to Gotoassist API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise GotoassistNotConnected()
        params = params or {}
        response = self.session.post(self._get_url_request(name), json=params, headers=self.headers)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise GotoassistRequestException(str(e))
        return response.json()

    def _get(self, name, params=None):
        """ Serves a GET request to Gotoassist API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise GotoassistNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params, headers=self.headers)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise GotoassistRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses Gotoassisst's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        offset = 0
        companies_list = []
        companies_raw = self._get('/G2A/rest/v1/companies', params={'limit': 50, 'offset': offset})
        comapnies_count = companies_raw["totalNumCompanies"]
        self.logger.debug(f"Got {comapnies_count} Companies Count")
        companies_list += [company_raw["companyId"] for company_raw in companies_raw["companies"]]
        while comapnies_count > offset + 50:
            offset += 50
            companies_raw = self._get('/G2A/rest/v1/companies', params={'limit': 50, 'offset': offset})
            companies_list += [company_raw["companyId"] for company_raw in companies_raw["companies"]]
        self.logger.debug(f"Companies list is {str(companies_list)}")
        devices_list = []
        for company_id in companies_list:
            offset = 0
            devices_raw = self._get('/G2A/rest/v1/companies/' + str(company_id) +
                                    '/machines', params={'limit': 50, 'offset': offset})
            devices_count = devices_raw["totalNumMachines"]
            devices_list += devices_raw["machines"]
            while devices_count > offset + 50:
                offset += 50
                devices_raw = self._get('/G2A/rest/v1/companies/' + str(company_id) +
                                        '/machines', params={'limit': 50, 'offset': offset})
                devices_list += devices_raw["machines"]
        return devices_list

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
