import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from symantec_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecConnection(RESTConnection):
    def __init__(self, *args, username_domain: str = '', **kwargs):
        super().__init__(*args, **kwargs)
        self._username_domain = username_domain
        self.__token = None
        self.__adminId = None

    def __set_token(self, token, adminId):
        """ Sets the API token (as the connection credentials)

        :param str token: API Token
        :param str adminId: user adminId
        """
        self.__token = token
        self.__adminId = adminId
        self._session_headers['Authorization'] = 'Bearer ' + self.__token

    def _connect(self):
        if self._username is not None and self._password is not None and self._username_domain is not None:
            connection_dict = {
                'username': self._username,
                'password': self._password,
                'domain': self._username_domain
            }
            response = self._post('identity/authenticate', body_params=connection_dict)
            if 'token' not in response:
                error = response.get('errorCode', 'unknown connection error')
                message = response.get('errorMessage', '')
                if message != '':
                    error += ':' + message
                raise RESTException(error)
            self.__set_token(response['token'], response['adminId'])
            self._get('computers', url_params={'pageSize': 1, 'pageIndex': 1})
        else:
            raise RESTException('no username or password and no token')

    def close(self):
        """ Closes the connection """
        if self.__token:
            self._post('identity/logout', body_params={'token': self.__token,
                                                       'adminId': self.__adminId}, use_json_in_response=False)
        super().close()

    def get_device_list(self):
        current_clients_page = self._get('computers',
                                         url_params={'pageSize': consts.DEVICES_PER_PAGE,
                                                     'pageIndex': 1})
        yield from current_clients_page['content']
        last_page = current_clients_page['lastPage']
        totalPages = current_clients_page['totalPages']
        page_num = 2
        exception_in_row = 0
        while not last_page and page_num <= totalPages:
            try:
                current_clients_page = self._get('computers',
                                                 url_params={'pageSize': consts.DEVICES_PER_PAGE,
                                                             'pageIndex': page_num})
                yield from current_clients_page['content']
                last_page = current_clients_page['lastPage']
                exception_in_row = 0
            except Exception:
                logger.exception(f'Got error on page {page_num}, skipping')
                exception_in_row += 1
                if exception_in_row >= 100:
                    break
            page_num += 1
            logger.debug(f'Got {page_num*consts.DEVICES_PER_PAGE} devices so far')
