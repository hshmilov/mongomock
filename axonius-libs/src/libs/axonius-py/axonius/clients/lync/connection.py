import datetime
import logging
import re
from random import random

from axonius.clients.lync.consts import INTERNAL_DISCOVER_URL, DISCOVER_URL, MAX_NUMBER_OF_USERS, AUTH_URL_REGEX
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class LyncConnection(RESTConnection):
    """ rest client for Lync adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = None
        self._expiration_timeout = None
        self._auth_url = None
        self._applications_url = None
        self._domain = self._domain.strip('https://').strip('http://')

    def _set_token(self):
        if (self._expiration_timeout and self._expiration_timeout > datetime.datetime.now()) or not self._auth_url:
            return

        body_params = {
            'grant_type': 'password',
            'username': self._username,
            'password': self._password
        }

        response = self._post(self._auth_url, body_params=body_params, force_full_url=True)
        self._token = response.get('access_token')
        self._expiration_timeout = datetime.datetime.now() + datetime.timedelta(response.get('expires_in'))
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        # Make refresh token request

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            response = self._get(INTERNAL_DISCOVER_URL.format(domain=self._domain), raise_for_status=False,
                                 return_response_raw=True, force_full_url=True)
            # If internal url doesn't work. we will try to do the regular url.
            if response.status_code != 200:
                response = self._get(DISCOVER_URL.format(domain=self._domain), raise_for_status=False,
                                     return_response_raw=True, force_full_url=True)

            response = response.json()

            links = response.get('_links')
            if not (isinstance(links, dict) and (
                    isinstance(links.get('OAuth'), dict) or isinstance(links.get('user'), dict))):
                raise RESTException(f'Invalid response {response}')

            auth_url = links.get('OAuth').get('href') or links.get('user').get('href')
            if not auth_url:
                raise RESTException(f'Invalid response {response}')

            # We are supposed to get in the response header the authentication url.
            response = self._get(auth_url, raise_for_status=False, return_response_raw=True, force_full_url=True)
            if not response.headers.get('WWW-Authenticate'):
                raise RESTException(f'Invalid response {response}')
            auth_url = response.headers.get('WWW-Authenticate').split(',')[0]
            self._auth_url = re.search(AUTH_URL_REGEX, auth_url).group(1)

            response = response.json()

            # In the response there supposed to be applications url.
            if not (isinstance(response.get('_links'), dict) and
                    isinstance(response.get('_links').get('applications'), dict) and
                    response.get('_links').get('applications').get('href')):
                raise RESTException(f'Invalid response {response}')

            self._applications_url = response.get('_links').get('applications').get('href')

            self._set_token()

            body_params = {
                'UserAgent': 'UCWA Lync',
                # We are supposed to give some unique endpoint id for the connection.
                'EndpointId': f'{random.randint(0, 1000000000)}',
                'Culture': 'en-US',
            }

            self._post(self._applications_url, body_params=body_params, force_full_url=True)

        except Exception as e:
            raise Exception(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get(self, *args, **kwargs):
        self._set_token()
        return super()._get(*args, force_full_url=True, **kwargs)

    def get_device_list(self):
        pass

    def _get_users(self):
        try:
            total_fetched_users = 0

            body_params = {
                'UserAgent': 'UCWA Lync',
                'EndpointId': f'{random.randint(0, 1000000000)}',
                'Culture': 'en-US',
            }

            self._set_token()

            response = self._post(self._applications_url, body_params=body_params, force_full_url=True)
            if not (isinstance(response, dict) and
                    isinstance(response.get('people'), dict) and
                    isinstance(response.get('people').get('myContacts'), dict) and
                    response.get('people').get('myContacts').get('href')):
                logger.warning(f'Received invalid response for users: {response}')
                return

            contacts_url_suffix = response.get('people').get('myContacts').get('href')

            response = self._get(f'{self._applications_url}{contacts_url_suffix}', force_full_url=True)
            if not (isinstance(response, dict) and
                    isinstance(response.get('_embedded'), dict) and
                    isinstance(response.get('_embedded').get('contact'), list)):
                logger.warning(f'Received invalid response for users: {response}')
                return

            for contact in response.get('_embedded').get('contact'):
                if not isinstance(contact, dict):
                    logger.warning(f'Received invalid contact: {contact}')
                    continue
                yield contact
                total_fetched_users += 1
                if total_fetched_users >= MAX_NUMBER_OF_USERS:
                    logger.info('Got max users')
                    break

            logger.info(f'Got total of {total_fetched_users} users')
        except Exception as err:
            logger.exception(f'Invalid request made while fetching users {str(err)}')
            raise

    def get_user_list(self):
        try:
            yield from self._get_users()
        except RESTException as err:
            logger.exception(str(err))
            raise
