import requests
import logging
logger = logging.getLogger(f"axonius.{__name__}")
from service_now_adapter.consts import *
from service_now_adapter.exceptions import ServiceNowAlreadyConnected, ServiceNowConnectionError, ServiceNowNotConnected, \
    ServiceNowRequestException


class ServiceNowConnection(object):
    def __init__(self, domain, verify_ssl, number_of_offsets, offset_size):
        """ Initializes a connection to ServiceNow using its rest API

        :param str domain: domain address for ServiceNow
        :param bool verify_ssl Verify the ssl
        """
        self.domain = domain
        url = domain
        if not url.lower().startswith('https://'):
            url = 'https://' + url

        if not url.endswith('/'):
            url += '/'
        url += 'api/now/'
        self.url = url
        self.session = None
        self.username = None
        self.password = None
        self.verify_ssl = verify_ssl
        self.number_of_offsets = number_of_offsets
        self.offset_size = offset_size
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

    def connect(self):
        """ Connects to the service """
        if self.is_connected:
            raise ServiceNowAlreadyConnected()
        session = requests.Session()
        if self.username is not None and self.password is not None:
            response = session.get(self._get_url_request('table/cmdb_ci_computer?sysparm_limit=1'),
                                   auth=(self.username, self.password), verify=self.verify_ssl)
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                raise ServiceNowConnectionError(str(e))
        else:
            raise ServiceNowConnectionError("No user name or password")
        self.session = session

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def close(self):
        """ Closes the connection """
        self.session.close()
        self.session = None

    def _post(self, name, params=None):
        """ Serves a POST request to ServiceNow API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise ServiceNowNotConnected()
        params = params or {}
        response = self.session.post(self._get_url_request(name), json=params,
                                     headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ServiceNowRequestException(str(e))
        return response.json()

    def _get(self, name, params=None):
        """ Serves a GET request to ServiceNow API

        :param str name: the name of the request
        :param dict params: Additional parameters
        :return: the response
        :rtype: dict
        """
        if not self.is_connected:
            raise ServiceNowNotConnected()
        params = params or {}
        response = self.session.get(self._get_url_request(name), params=params,
                                    headers=self.headers, verify=self.verify_ssl)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise ServiceNowRequestException(str(e))
        return response.json()

    def get_device_list(self, **kwargs):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses ServiceNow's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        tables_devices = []
        for table_details in TABLES_DETAILS:
            new_table_details = table_details.copy()
            table_devices = {DEVICES_KEY: self.get_devices_from_table(table_details[TABLE_NAME_KEY])}
            new_table_details.update(table_devices)
            tables_devices.append(new_table_details)
        return tables_devices

    def get_devices_from_table(self, table_name):
        table_results = []
        for sysparm_offset in range(0, self.number_of_offsets):
            try:
                table_resuls_paged = self._get('table/' + str(table_name) +
                                               '?sysparm_limit=' + str(self.offset_size) + '&sysparm_offset=' + str(sysparm_offset * self.offset_size))
                if len(table_resuls_paged.get("result", [])) == 0:
                    break
                table_results += table_resuls_paged.get("result", [])

            except Exception:
                logger.exception(f"Got exception in offset {sysparm_offset} with table {table_name}")
                break
        logger.info(f"Got {len(table_results)} devices from table: {table_name}")
        return table_results

    def add_dict_to_table(self, dict_data, table_name):
        self._post('table/' + str(table_name), dict_data)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
