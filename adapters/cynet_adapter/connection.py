import logging
import json

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class CynetConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        """ Initializes a connection to cynet using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for cynet
        """
        super().__init__(url_base_prefix='api', *args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json',
                                   'Accept': 'application/json'}

    def _connect(self):
        """ Connects to the service """
        if self._username and self._password:
            self._token = self._post('account/token', body_params={'user_name': self._username,
                                                                   'password': self._password})['access_token']
            self._session_headers['access_token'] = self._token
        else:
            raise RESTException('No username of password')

    def get_device_list(self):
        """ Returns a list of all agents

        :param dict kwargs: api query *string* parameters (ses cynet's API documentation for more info)
        :return: the response
        :rtype: dict
        """
        yield from self.__do_query('select * from indicators.hosts')

    def __do_query(self, query):
        response = self._post('sql/runQuery', body_params=query, use_json_in_body=False,
                              use_json_in_response=False)

        tables = json.loads(response.decode('utf-8'))['tables']
        for table in tables:
            try:
                yield from table['table']
            except Exception:
                logger.exception(f'Problem getting table')
