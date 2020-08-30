import logging
from datetime import datetime

import pytz

from axonius.clients.rest.connection import RESTConnection, RestList, RestDict
from axonius.clients.rest.exception import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import int_or_none
from .consts import AUTHENTICATION_URL, DEFAULT_EXPIRES_IN, EXPIRE_EPSILON, USERS_URL, \
    MAX_NUMBER_OF_USERS, USER_PER_PAGE, APPS_PER_USER, BODY_PARAMS

logger = logging.getLogger(f'axonius.{__name__}')


class OneloginConnection(RESTConnection):
    """ rest client for Onelogin adapter """

    def __init__(self, client_id, client_secret, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._session_refresh = None
        self._access_token = None
        self._token_timeout = DEFAULT_EXPIRES_IN - EXPIRE_EPSILON
        self._token_creation_date = None
        self._client_id = client_id
        self._client_secret = client_secret

    def _set_token(self):
        self._session_headers['Authorization'] = f'client_id:{self._client_id}, client_secret:{self._client_secret}'
        response = self._post(AUTHENTICATION_URL, body_params=BODY_PARAMS, response_type=dict)

        self._access_token = response.get('access_token')
        if not self._access_token:
            raise RESTException(f'Couldn\'t fetch access token from response: {response}')

        self._token_timeout = int_or_none(response.get('expires_in')) or DEFAULT_EXPIRES_IN
        self._token_timeout -= EXPIRE_EPSILON
        self._token_creation_date = parse_date(response.get('created_at'))
        self._session_headers['Authorization'] = f'Bearer {self._access_token}'

    def _connect(self):
        if not (self._client_id and self._client_secret):
            raise RESTException('No client id or client secret')
        try:
            self._set_token()
            self._get(USERS_URL)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get(self, *args, **kwargs):
        """
         Overrides _get function in order to set token if it expires.
        """
        utcnow = datetime.utcnow()
        utcnow = utcnow.replace(tzinfo=pytz.utc)
        if (utcnow - self._token_creation_date).total_seconds() >= self._token_timeout:
            self._set_token()
        return super()._get(*args, **kwargs)

    def _get_apps_by_user(self, user_id: int):
        try:
            response = self._get(APPS_PER_USER.format(user_id=user_id), response_type=dict)
            return RestList(response.get('data', expected_type=list), expected_type=dict)
        except Exception as err:
            logger.exception(f'Invalid request made while getting apps by user {str(err)}')
            return []

    def get_device_list(self):
        try:
            pass
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _paginated_user_get(self):
        try:
            number_of_users = 0
            response = self._get(USERS_URL, url_params={'limit': USER_PER_PAGE}, response_type=dict)
            users = response.get('data', expected_type=list)
            users = RestList(users, expected_type=dict)
            pagination = response.get('pagination', expected_type=dict)
            next_link = pagination.get('next_link')

            while users:
                for user in users:
                    user = RestDict(user)
                    user_id = user.get('id', expected_type=int)
                    user['apps'] = self._get_apps_by_user(user_id)
                    yield user
                    number_of_users += 1
                    if number_of_users >= MAX_NUMBER_OF_USERS:
                        logger.info(
                            f'Got maximum of users: {number_of_users}')
                        break

                if number_of_users >= MAX_NUMBER_OF_USERS:
                    break

                if not next_link:
                    logger.info(f'Done paginating users, got {number_of_users} users')
                    break

                response = self._get(next_link, response_type=dict)
                users = response.get('data', expected_type=list)
                users = RestList(users, expected_type=dict)
                pagination = response.get('pagination', expected_type=dict)
                next_link = pagination.get('next_link')

        except Exception as err:
            logger.exception(f'Invalid request made while paginating users {str(err)}')
            raise

    def get_user_list(self):
        try:
            yield from self._paginated_user_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
