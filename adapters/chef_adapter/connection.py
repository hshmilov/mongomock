from urllib3.util.url import parse_url
import chef
from chef_adapter.exceptions import ChefConnectionError, ChefRequestException


class ChefConnection(object):
    def __init__(self, logger, domain: str, organization: str, client_key: bytes, client: str, ssl_verify=False):
        """ Initializes a connection to Chef using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Chef
        """
        self.logger = logger
        url = "https://{}".format(parse_url(domain).hostname, organization)
        key = chef.rsa.Key(client_key)
        self._chef_connection = chef.ChefAPI(url=url, key=key, client=client, ssl_verify=ssl_verify)
        self.url = '/organizations/' + organization

    def _get_url_request(self, request_name=''):
        """ Builds and returns the full url for the request

        :param request_name: the request name
        :return: the full request url
        """
        return self.url + request_name

    def connect(self):
        """ Connects to the service """
        try:
            self._chef_connection.api_request('Get', path=self._get_url_request())
        except Exception as err:
            message = f'Error connecting to chef-server {self._chef_connection.url}{self.url} for client ' \
                      f'{self._chef_connection.client}'
            self.logger.exception(message)
            raise ChefConnectionError(message)

    def __del__(self):
        self.logout()

    def logout(self):
        """ Logs out of the service"""
        self.close()

    def close(self):
        """ Closes the connection """

    def get_devices(self):
        """ Returns a list of all agents

        :param str data: the body of the request
        :return: the response
        :rtype: dict
        """
        client_list = []
        last_id = 0
        total = 1
        try:
            while last_id < total:
                response = self._chef_connection.api_request('Get', self._get_url_request(
                    f'/search/node?rows=1000&start={last_id}'))
                client_list.extend(response['rows'])
                last_id = len(client_list)
                total = response['total']
                self.logger.info(f"Got {last_id} devices so far out of {total}")
        except Exception as err:
            message = f'Error fetching nodes for {self._chef_connection.url}' \
                      f'{self.url}/search/node?rows=1000&start={last_id}'
            self.logger.exception(message)
            raise ChefRequestException(message)
        return client_list

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
