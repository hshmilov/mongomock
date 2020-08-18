import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.datetime import parse_date
from hp_ilo_adapter.consts import SYSTEM_API_SUFFIX, MAX_NUMBER_OF_DEVICES, API_AUTH_SUFFIX, DEFAULT_TOKEN_EXPIRATION

logger = logging.getLogger(f'axonius.{__name__}')


class HpIloConnection(RESTConnection):
    """ rest client for HpIlo adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._session_refresh = None

    def _refresh_token(self):
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return

        self._get_token()

    def _get_token(self):
        try:
            body_params = {
                'UserName': self._username,
                'Password': self._password
            }

            response = self._post(API_AUTH_SUFFIX, body_params=body_params,
                                  return_response_raw=True, use_json_in_response=False)

            if not response.headers.get('X-Auth-Token'):
                # pylint: disable=logging-format-interpolation
                logger.exception(f'Failed receiving token while trying to connect. {str(response)}')
                raise RESTException(f'Failed receiving token while trying to connect. {str(response)}')

            auth_token = response.headers.get('X-Auth-Token')
            self._session_headers['X-Auth-Token'] = auth_token

            session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=(DEFAULT_TOKEN_EXPIRATION - 50))
            if (isinstance(response.json(), dict) and
                    isinstance(response.json().get('Oem'), dict) and
                    isinstance(response.json().get('Oem').get('Hpe'), dict) and
                    response.json().get('Oem').get('Hpe').get('UserExpires')):
                session_refresh = parse_date(
                    response.json().get('Oem').get('Hpe').get('UserExpires')) - datetime.timedelta(seconds=50)

            self._session_refresh = session_refresh

        except Exception as e:
            logger.exception('Error: Failed getting token, invalid request was made.')
            raise ValueError(f'Error: Failed getting token, invalid request was made. {str(e)}')

    # pylint: disable=logging-format-interpolation
    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._get_token()

            response = self._get(SYSTEM_API_SUFFIX)
            if not (isinstance(response, dict) and
                    isinstance(response.get('Members'), list) and
                    len(response.get('Members'))):
                logger.error(f'Received invalid response while trying to connect. {response}')
                raise RESTException(f'Received invalid response while trying to connect. {response}')

            first_member = response.get('Members')[0]
            if not (isinstance(first_member, dict) and first_member.get('@odata.id')):
                logger.error(f'Received invalid url while checking connection. {first_member}')
                raise ValueError(f'Received invalid url while checking connection. {first_member}')

            first_member_url = first_member.get('@odata.id')
            if isinstance(first_member_url, str):
                if first_member_url.startswith('/'):
                    first_member_url = first_member_url[1:]
            self._get(first_member_url)

        except Exception as err:
            logger.exception(f'Failed establish a connecting, {str(err)}')
            raise

    def _get_system_devices(self):
        try:
            total_devices = 0

            response = self._get(SYSTEM_API_SUFFIX, do_basic_auth=True)
            if not (isinstance(response, dict) and
                    isinstance(response.get('Members'), list)):
                logger.error(f'Received invalid response while trying to connect. {response}')
                raise RESTException(f'Received invalid response while trying to connect. {response}')

            for member in response.get('Members'):
                if not (isinstance(member, dict) and member.get('@odata.id')):
                    logger.warning(f'Received invalid member while fetching devices. {member}')
                    continue

                member_url = member.get('@odata.id')
                if isinstance(member_url, str):
                    if member_url.startswith('/'):
                        member_url = member_url[1:]

                member_data = self._get(member_url, do_basic_auth=True)
                if isinstance(member_data, dict):
                    yield member_data
                    total_devices += 1

                if total_devices >= MAX_NUMBER_OF_DEVICES:
                    logger.info(f'Reached max number of devices {total_devices} / {len(response.get("Members"))}')
                    break

            logger.info(f'Got total of {total_devices} devices')
        except Exception:
            logger.exception(f'Invalid request was made while getting device')
            raise

    def get_device_list(self):
        try:
            yield from self._get_system_devices()
        except RESTException as err:
            logger.exception(str(err))
            raise
