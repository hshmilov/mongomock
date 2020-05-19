import logging
from collections import defaultdict
import datetime
import time
import jwt

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from pure_storage_flash_array_adapter.consts import API_OAUTH_PREFIX, API_PREFIX, EXPIRE_SECONDS, DEVICE_PER_PAGE, \
    ACCESS_TOKEN_GRANT_TYPE_PARAM, ACCESS_TOKEN_SUBJECT_TOKEN_TYPE, NULL_STR

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class PureStorageFlashArrayConnection(RESTConnection):
    """ rest client for PureStorageFlashArray adapter """

    def __init__(self, *args, application_id, private_key, **kwargs):
        super().__init__(*args,
                         url_base_prefix=API_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._jwt = None
        self._token = None
        self._token_type = None
        self._token_expires = None
        self._private_key = private_key
        self._application_id = application_id

    def _refresh_token(self):
        if self._token_expires and self._token_expires > datetime.datetime.now():
            return

        self._create_jwt_token()
        self._get_access_token()

    def _get_access_token(self):
        try:
            body_params = {
                'grant_type': ACCESS_TOKEN_GRANT_TYPE_PARAM,
                'subject_token': self._jwt,
                'subject_token_type': ACCESS_TOKEN_SUBJECT_TOKEN_TYPE
            }
            response = self._post(API_OAUTH_PREFIX, body_params=body_params)
            if not (isinstance(response, dict) and response.get('access_token')):
                raise RESTException(f'Failed fetching access token, received invalid response: {response}')

            self._token = response.get('access_token')
            self._token_type = response.get('token_type')
            self._token_expires = datetime.datetime.now() + datetime.timedelta(seconds=response.get('expires_in'))

            self._session_headers['Authorization'] = f'{self._token_type} {self._token}'
        except Exception:
            raise ValueError(f'Error: Failed getting token, invalid request was made.')

    def _create_jwt_token(self):
        payload = {
            'iss': self._application_id,  # application id
            'iat': int(time.time()),  # current time
            'exp': int(time.time()) + EXPIRE_SECONDS  # expiration of JWT token
        }
        # pylint: disable=no-member
        new_jwt = jwt.encode(payload,
                             self._private_key,
                             algorithm='RS256')

        # python3 jwt returns bytes
        self._jwt = new_jwt.decode('utf-8')
        if not self._jwt:
            raise ValueError(f'Error: Failed getting jwt token.')

    def _get(self, *args, **kwargs):
        """
        Overriding _get for checking and refresh token automatic if needed
        :param args: args for RESTConnection._get()
        :param kwargs: kwargs for RESTConnection._get()
        :return: see RESTConnection._get()
        """
        self._refresh_token()
        return super()._get(*args, **kwargs)

    def _connect(self):
        if not self._private_key:
            raise RESTException('Private Key is required')
        if not self._application_id:
            raise RESTException('Application ID is required')

        try:
            self._create_jwt_token()
            self._get_access_token()

            url_params = {
                'limit': 1
            }
            self._get('arrays', url_params=url_params)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _paginated_arrays(self):
        try:
            network_interfaces = self._get_network_interfaces()

            url_params = {
                'limit': DEVICE_PER_PAGE,
                'continuation_token': NULL_STR
            }
            response = self._get('arrays', url_params=url_params)
            if not (isinstance(response, dict) and isinstance(response.get('items'), list)):
                logger.warning(f'Received invalid response for arrays. {response}')
                return

            for array in response.get('items'):
                if isinstance(array, dict) and array.get('id'):
                    array['network_interfaces'] = network_interfaces[array.get('id')]
                yield array

            while response.get('continuation_token'):
                url_params['continuation_token'] = response.get('continuation_token')
                response = self._get('arrays', url_params=url_params)
                if not (isinstance(response, dict) and isinstance(response.get('items'), list)):
                    logger.warning(f'Received invalid response for arrays. {response}')
                    break

                for array in response.get('items'):
                    if isinstance(array, dict) and array.get('id'):
                        array['network_interfaces'] = network_interfaces[array.get('id')]
                    yield array

        except Exception as err:
            logger.exception(f'Invalid request made for arrays, {str(err)}')
            raise

    def _get_network_interfaces(self):
        try:
            network_interfaces = defaultdict(list)
            url_params = {
                'limit': DEVICE_PER_PAGE,
                'continuation_token': NULL_STR
            }
            response = self._get('network-interfaces', url_params=url_params)
            if not (isinstance(response, dict) and isinstance(response.get('items'), list)):
                logger.warning(f'Received invalid response for network interfaces. {response}')
                return {}

            for network_interface in response.get('items'):
                if not (isinstance(network_interface, dict) and isinstance(network_interface.get('arrays'), list)):
                    continue
                for array in network_interface.get('arrays'):
                    if isinstance(array, dict) and array.get('id'):
                        network_interfaces[array.get('id')].append(network_interface)

            while response.get('continuation_token'):
                url_params['continuation_token'] = response.get('continuation_token')
                response = self._get('network-interfaces', url_params=url_params)
                if not (isinstance(response, dict) and isinstance(response.get('items'), list)):
                    logger.warning(f'Received invalid response for network interfaces. {response}')
                    break

                for network_interface in response.get('items'):
                    if not (isinstance(network_interface, dict) and isinstance(network_interface.get('arrays'), list)):
                        continue
                    for array in network_interface.get('arrays'):
                        if isinstance(array, dict) and array.get('id'):
                            network_interfaces[array.get('id')].append(network_interface)

            return network_interfaces
        except Exception as err:
            logger.exception(f'Invalid request made for network interfaces, {str(err)}')
            raise

    def _paginated_device_get(self):
        try:
            yield from self._paginated_arrays()
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
