import datetime
import logging
from enum import Enum

from axonius.clients.abstract.abstract_vault_connection import (AbstractVaultConnection,
                                                                VaultException,
                                                                VaultProvider)
from axonius.clients.rest.exception import RESTException, RESTRequestException
from axonius.clients.thycotic_vault.consts import MAX_NUMBER_OF_USERS, USERS_URL, USER_PER_PAGE
from axonius.utils.parsing import int_or_none, parse_bool_from_raw

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

    def _get(self, *args, **kwargs):
        # Due to a bug in the authentication of Thycotic we need to refresh the token each time we use _get.
        if self._refresh_token:
            self.refresh_token()
        else:
            self._auth_token()

        return super()._get(*args, **kwargs)

    def query_password(self, adapter_field_name, vault_data) -> str:
        """
        :param adapter_field_name: adapter gui filed name
        :param vault_data: [secret_id,vault_field_name]
        :return: secret entity password
        """
        try:

            secret_id = str(vault_data.get('secret'))
            vault_field = vault_data.get('field')

            if self._is_connected:
                self._connect()
            else:
                self.connect()

            if not secret_id or not vault_field:
                raise ThycoticVaultException(adapter_field_name, 'invalid missing secret id or password field')

            response = self._get(f'api/v1/secrets/{secret_id}')

        except Exception:
            message = f'Failed to fetch password. Secret ID: {secret_id}. Field Name: {vault_field}'
            logger.exception(message)
            raise ThycoticVaultException(adapter_field_name, message)

        password = self._get_attribute_value(attributes=response.get('items'), attribute_name=vault_field)

        if password is None:
            raise ThycoticVaultException(adapter_field_name,
                                         f'Secret not found. Secret ID: {secret_id}. Field Name: {vault_field}')
        return password

    def get_user_list(self):
        try:
            yield from self._get_users()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def test_adapter_permissions(self):
        """
        This function is created in order to check if the connection is valid.
        it is separated from _connect because this class is used also for vault and not only for adapter.

        """
        url_params = {
            'take': 1,
            'filter.includeInactive': True
        }

        try:
            self._get(USERS_URL, url_params=url_params)
        except Exception as e:
            message = f'Error: Invalid response from server, please check domain or credentials. {str(e)}'
            logger.exception(message)
            raise RESTException(message)

    def _get_users(self):
        try:
            number_of_users = 0
            url_params = {
                'take': USER_PER_PAGE,
                'filter.includeInactive': True
            }

            response = self._get(USERS_URL, url_params=url_params)
            if not isinstance(response, dict):
                raise RESTException(f'Response not in the correct format: {response}')

            total_results = int_or_none(response.get('total'))
            if not total_results:
                raise RESTException(f'Response does not contain total: {response}')

            logger.info(
                f'Expecting {total_results} users, out of a maximum of {MAX_NUMBER_OF_USERS}. '
                f'Overflow will be cut-off.')
            total_results = min(total_results, MAX_NUMBER_OF_USERS)

            while number_of_users <= total_results:
                users = response.get('records')
                if not isinstance(users, list):
                    logger.error(f'Users not in the correct format: {users}')
                    break

                for user in users:
                    if not isinstance(user, dict):
                        logger.warning(f'User not in the correct format: {user}')
                        continue
                    yield user
                    number_of_users += 1

                if not parse_bool_from_raw(response.get('hasNext')):
                    logger.info(f'Finished fetching users, collected {number_of_users} users')
                    break

                next_skip = int_or_none(response.get('nextSkip'))
                if not isinstance(next_skip, int):
                    logger.warning(f'Response does not contain nextSkip in correct format: {response}')
                    break
                url_params = {
                    'skip': next_skip,
                    'take': USER_PER_PAGE,
                    'filter.includeInactive': True
                }
                response = self._get(USERS_URL, url_params=url_params)
                if not isinstance(response, dict):
                    logger.warning(f'Response not in the correct format: {response}')
                    break

        except Exception as err:
            logger.exception(f'Invalid request made while paginating users {str(err)}')
            raise
