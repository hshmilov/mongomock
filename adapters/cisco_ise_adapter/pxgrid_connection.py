import logging
import random
import contextlib
import time

import axonius.utils.json as jsonutils
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cisco_ise_adapter.consts import (ISE_PXGRID_PORT, CiscoIseDeviceType,
                                      PXGRID_URL_BASE_PREFIX, PXGRID_TIME_TO_SLEEP_BETWEEN_TRIES,
                                      PXGRID_MAX_ACTIVATE_RETRIES)

logger = logging.getLogger(f'axonius.{__name__}')


class UserNonExistsError(Exception):
    pass


class CiscoIsePxGridConnection(RESTConnection):
    """
    Class to configure Cisco ISE via the ERS API
    """

    def __init__(self, *args, date_filter=None, **kwargs):
        super().__init__(
            *args,
            port=ISE_PXGRID_PORT,
            url_base_prefix=PXGRID_URL_BASE_PREFIX,
            headers={'Connection': 'keep_alive',
                     'Accept': 'application/json',
                     'Content-Type': 'application/json'},
            **kwargs
        )
        self._secret = None
        self._get_sessions_path = None
        self._date_filter = date_filter

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        if 'do_basic_auth' not in kwargs:
            kwargs['do_basic_auth'] = True

        return super()._do_request(*args, **kwargs)

    @staticmethod
    def test_reachability(domain):
        return RESTConnection.test_reachability(domain, port=ISE_PXGRID_PORT, path=PXGRID_URL_BASE_PREFIX, ssl=True)
    # pylint: enable=arguments-differ

    def _post(self, *args, **kwargs):
        # protocol requires empty json when no data
        if kwargs.get('body_params') is None:
            kwargs['body_params'] = {}
        return super()._post(*args, **kwargs)

    def _create_user(self):
        # no user provided, need to create account
        response = self._post('control/AccountCreate',
                              body_params={'nodeName': 'Axonius_' + str(random.randint(10000, 99999))},
                              do_basic_auth=False)
        if not jsonutils.is_valid(response, 'userName', 'password'):
            raise RESTException(f'control/AccountCreate bad response: {response}')
        self._username = response['userName']
        self._password = response['password']

    def _account_activate(self):

        # According the following example, it may take the account up to 60 seconds to be activated
        # https://developer.cisco.com/docs/pxgrid/#!retrieving-radius-failure-messages/output
        response = None
        for i in range(PXGRID_MAX_ACTIVATE_RETRIES):
            response_raw = self._post('control/AccountActivate',
                                      raise_for_status=False,
                                      return_response_raw=True,
                                      use_json_in_response=False)
            if response_raw.status_code == 401:
                raise UserNonExistsError()

            response = self._handle_response(response_raw)

            if not jsonutils.is_valid(response, 'accountState'):
                raise RESTException(f'control/AccountActivate bad response: {response}')

            if response['accountState'] == 'ENABLED':
                break

            logger.debug(f'Retry {i} - Account \'{self._username}\' not activated yet,'
                         f' sleeping {PXGRID_TIME_TO_SLEEP_BETWEEN_TRIES} seconds')
            time.sleep(PXGRID_TIME_TO_SLEEP_BETWEEN_TRIES)

        if not (response and response['accountState'] == 'ENABLED'):
            msg = f'Please make sure ‘{self._username}’ is authorized in pxGrid Services on your Cisco ISE domain'
            raise RESTException(msg)

        logger.info(f'Account {self._username} activated succesfully')

    def _account_create_and_activate(self):
        """ create an account if needed and activate it """
        if not self._username and not self._password:
            self._create_user()
        try:
            self._account_activate()
        except UserNonExistsError:
            self._create_user()
            self._account_activate()

    def _connect(self):
        self._account_create_and_activate()

        response = self._post('control/ServiceLookup',
                              body_params={'name': 'com.cisco.ise.session'})

        if not jsonutils.is_valid(response, {'services': [{'properties': 'restBaseUrl'}, 'nodeName']}):
            raise RESTException(f'control/serviceLookup bad response: {response}')

        service = response['services'][0]

        url = service['properties']['restBaseUrl']
        logger.info(f'url = {url}')
        path = f'{url}/getSessions'
        node_name = service['nodeName']

        response = self._post('control/AccessSecret',
                              body_params={'peerNodeName': node_name})
        if 'secret' not in response:
            raise RESTException(f'control/AccessSecret bad response: {response}')
        secret = response['secret']

        self._get_sessions_path = path
        self._secret = secret

    @contextlib.contextmanager
    def secret(self):
        """ contextmanager to apply secret and node name as creds """
        password = self._password

        try:
            self._password = self._secret
            yield
        finally:
            self._password = password

    def get_device_list(self):
        body_params = {}
        if self._date_filter:
            body_params = {'startTimestamp': self._date_filter}
        with self.secret():
            response = self._post(self._get_sessions_path, force_full_url=True, body_params=body_params)
        if not (isinstance(response, dict) and isinstance(response.get('sessions'), list)):
            logger.error(f'Invalid response retrieved: {response}')
            return
        sessions = response['sessions']
        logger.info(f'Yielding {len(sessions)} sessions')
        for session in sessions:
            yield (CiscoIseDeviceType.LiveSessionDevice.name, session)
