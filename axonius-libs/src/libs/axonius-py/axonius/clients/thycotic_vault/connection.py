import logging
from enum import Enum
import datetime

from axonius.clients.abstract.abstract_vault_connection import (AbstractVaultConnection,
                                                                VaultException,
                                                                VaultProvider)
from axonius.clients.rest.exception import RESTException, RESTRequestException

logger = logging.getLogger(f'axonius.{__name__}')

ACCESS_TOKEN = 'access_token'
REFRESH_TOKEN = 'refresh_token'
SECRET_SERVER_URI = '/SecretServer'


class AuthGrantType(Enum):
    Password = 'password'
    RefreshToken = 'refresh_token'

    def __str__(self):
        return self.value


class ThycoticVaultException(VaultException):

    def __init__(self, field_name, *args, **kwargs):
        super().__init__(VaultProvider.Thycotic, field_name, *args, **kwargs)


class ThycoticVaultConnection(AbstractVaultConnection):

    def __init__(self,
                 host: str,
                 port: int,
                 username: str,
                 password: str,
                 verify_ssl: bool,
                 *args,
                 **kwargs):

        super().__init__(domain=host,
                         port=port,
                         url_base_prefix=self.get_server_url_prefix(host),
                         username=username,
                         password=password,
                         verify_ssl=verify_ssl,
                         *args, **kwargs)

        self._username = username
        self._password = password

        self._token = {}
        self._refresh_token = None
        self._token_lifetime = None

    @staticmethod
    def get_server_url_prefix(host: str) -> str:
        """
        we support local Secret Server instalation or cloud base instance
        the difference from API point of view is the URI path 'SecretServer' required on local API calls
        HTTPS://<SECRET_SERVER>/SecretServer

        :param host: URL of secret server local or cloud
        :return:
        """
        return SECRET_SERVER_URI if (host.endswith(SECRET_SERVER_URI) or
                                     host.endswith(f'{SECRET_SERVER_URI}/')) else '/'

    def _token_handler(self, token: dict):
        self._token = token
        access_token = token.get(ACCESS_TOKEN)
        self._refresh_token = token.get(REFRESH_TOKEN)
        self._token_lifetime = datetime.datetime.now() + datetime.timedelta(seconds=token.get('expires_in'))
        self._session_headers['Authorization'] = f'Bearer {access_token}'

    def refresh_token(self):
        """
            https://thycotic.force.com/support/s/article/SS-HOW-EXT-How-to-Use-Tokens
        """

        # clean authz header from request
        self._session_headers = {}
        try:
            response = self._post('oauth2/token',
                                  body_params={
                                      'grant_type': AuthGrantType.RefreshToken,
                                      'refresh_token': 'd'
                                  },
                                  use_json_in_body=False,
                                  extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                  raise_for_status=False
                                  )

            if response and response.get('access_token'):
                logger.info('access token refreshed successfully')
                self._token_handler(response)
            else:
                logger.warning('refreshed token expired  or invalid , re-authenticating for new access token  ')
                self._auth_token()

        except RESTRequestException:
            # sometime server return HTML response instead of JSON respone when refreshed token expired
            logger.error('access token refreshed failed , re-authenticating for new access token ')
            self._auth_token()

    def _auth_token(self):
        """
        login and request access token
        """
        response = self._post('oauth2/token',
                              body_params={'username': self._username,
                                           'password': self._password,
                                           'grant_type': AuthGrantType.Password},
                              use_json_in_body=False,
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'}
                              )
        if response and response.get(ACCESS_TOKEN):
            self._token_handler(response)
        else:
            raise RESTException('Bad login Credentials')

    def _connect(self):
        """
        use current access token if exsits
        if expired then use refresh token to allocate new access token
        if no refresh token or
        """

        if self._token_lifetime and self._token_lifetime > datetime.datetime.now():
            return
        if self._refresh_token:
            self.refresh_token()
        else:
            self._auth_token()

    @staticmethod
    def _get_attribute_value(attributes: list = None, attribute_name: str = 'Password') -> str:
        """
        :param attributes:  - thycotic vault response is a list of item dict (attributes)
        :param attribute_name: i.e password
        :return: attribute_value


           "items": [
               {
                 "itemId": 1,
                 "fileAttachmentId": null,
                 "filename": null,
                 "itemValue": "vcenter.axonius.lan",
                 "fieldId": 178,
                 "fieldName": "Host",
                 "slug": "host",
                 "fieldDescription": "The ESX/ESXi host.",
                 "isFile": false,
                 "isNotes": false,
                 "isPassword": false
               },
                   ...
                   ...
               {
                 "itemId": 3,
                 "fileAttachmentId": null,
                 "filename": null,
                 "itemValue": "a$Xvje99a$Xvje99",
                 "fieldId": 180,
                 "fieldName": "Password",
                 "slug": "password",
                 "fieldDescription": "The password of the ESX/ESXi account.",
                 "isFile": false,
                 "isNotes": false,
                 "isPassword": true
                },
                ]
        """
        return next((item.get('itemValue') for item in attributes if item.get('fieldName') == attribute_name), None)

    def query_password(self, filed_name, query) -> str:
        """
        :param filed_name: gui filed name
        :param query: get secret by id
        :return: secret entity password
        """
        try:
            if self._is_connected:
                self._connect()
            else:
                self.connect()

            response = self._get(f'api/v1/secrets/{query}')

        except Exception as exc:
            logger.exception(f'Failed to fetch password from vault using query: {query}')
            raise ThycoticVaultException(filed_name, exc)

        password = self._get_attribute_value(attributes=response.get('items'))

        if password is None:
            logger.warning(f'No Password item  match for secret id {query}')
        return password
