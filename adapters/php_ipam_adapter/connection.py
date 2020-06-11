import logging
import datetime
from collections import defaultdict

from php_ipam_adapter.consts import API_PREFIX
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class PhpIpamConnection(RESTConnection):
    """ rest client for PhpIpam adapter """

    def __init__(self, *args, app_id, **kwargs):
        url_base_prefix = f'{API_PREFIX}/{app_id}'
        super().__init__(*args, url_base_prefix=url_base_prefix,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._app_id = app_id
        self._token = None
        self._token_expires = None

    def _refresh_token(self):
        if self._token_expires and self._token_expires > datetime.datetime.now():
            return

        self._get_token()

    def _get_token(self):
        try:
            response = self._post('user', do_basic_auth=True)
            if not (isinstance(response, dict) and
                    isinstance(response.get('data'). dict) and
                    response.get('data').get('token')):
                raise RESTException(f'Failed fetching access token, received invalid response: {response}')

            self._token = response.get('data').get('token')

            token_expires = parse_date(response.get('data').get('expires'))
            self._token_expires = token_expires - datetime.timedelta(seconds=100)

            self._session_headers = {
                'token': self._token.strip()
            }
        except Exception as e:
            raise ValueError(f'Error: Failed getting token from the server. {str(e)}')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        try:
            self._get_token()
            self._get('devices')

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    # There is no documentation about pagination, get all the info from a single get
    def _get_subnets(self):
        try:
            subnets = defaultdict(list)

            response = self._get('subnets')
            if not (isinstance(response, dict) and isinstance(response.get('data'), list)):
                logger.warning(f'Received invalid response for subnets. {response}')
                return subnets

            for subnet in response.get('data'):
                if isinstance(subnet, dict) and subnet.get('id'):
                    subnets[subnet.get('id')].append(subnet)

            return subnets
        except Exception as e:
            logger.debug(f'Failed getting subnets. {str(e)}')
            return {}

    # There is no documentation about pagination, get all the info from a single get
    def _get_devices(self):
        try:
            extra_subnets = self._get_subnets()

            response = self._get('devices')
            if not (isinstance(response, dict) and isinstance(response.get('data'), list)):
                logger.warning(f'Received invalid response for devices. {response}')
                return

            for device in response.get('data'):
                if not isinstance(device, dict):
                    logger.error(f'Incorrect type {type(device)} for device {device}')
                    break

                if device.get('id'):
                    device['extra_subnet'] = extra_subnets.get(device.get('id')) or {}

                yield device

        except Exception as e:
            logger.exception(f'Invalid request made while querying devices {str(e)}')
            raise

    def get_device_list(self):
        try:
            yield from self._get_devices()
        except RESTException as err:
            logger.exception(str(err))
            raise

    # There is no documentation about pagination, get all the info from a single get
    def _get_users(self):
        try:
            # TBD, after testing check values and add
            response = self._get('user/all')
            if not (isinstance(response, dict) and isinstance(response.get('data'), list)):
                logger.warning(f'Received invalid response for regular users. {response}')
                return {}

            logger.info(f'Regular user result: {response.get("data")}')
            # TBD - Test on field and implement
            # user/all request is not documented, therefor we first log the response and after we will be able to
            # fetch the correct data and build User Structure
            # for user in response.get('data'):
            #    yield user, 'regular'

            return {}
        except Exception as err:
            logger.exception(f'Invalid request made while paginating regular users {str(err)}')
            raise

    # There is no documentation about pagination, get all the info from a single get
    def _get_admins(self):
        try:
            # TBD, after testing check values and add
            response = self._get('user/admins')
            if not (isinstance(response, dict) and isinstance(response.get('data'), dict)):
                logger.warning(f'Received invalid response for admin users. {response}')
                return {}

            logger.info(f'Admin user result: {response.get("data")}')
            # TBD - Test on field and implement
            # user/admins request is not documented, therefor we first log the response and after we will be able to
            # fetch the correct data and build Admin User Structure
            # for user in response.get('data'):
            #    yield user, 'admin'

            return {}
        except Exception as err:
            logger.exception(f'Invalid request made while paginating admin users {str(err)}')
            raise

    # pylint:disable=no-self-use
    def get_user_list(self):
        try:
            yield from self._get_users()
            yield from self._get_admins()
        except RESTException as err:
            logger.exception(str(err))
