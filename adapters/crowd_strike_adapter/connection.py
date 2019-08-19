import time
import logging

from datetime import datetime, timedelta

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException, RESTRequestException
from crowd_strike_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


# XXX: For some reason this file doesn't ignore logging-fstring-interpolation
# although we got it in pylintrc ignore. add disable for it, and disable the disable warning
# pylint: disable=I0021
# pylint: disable=W1203
# api doc: https://assets.falcon.crowdstrike.com/support/api/swagger.html


class CrowdStrikeConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, headers={'Accept': 'application/json'})
        self.last_token_fetch = None
        self.requests_count = 0

    def refresh_access_token(self, force=False):
        if not self.last_token_fetch or (self.last_token_fetch + timedelta(minutes=20) < datetime.now()) or force:
            response = self._post('oauth2/token', use_json_in_body=False,
                                  body_params={'client_id': self._username,
                                               'client_secret': self._password})
            token = response['access_token']
            self._session_headers['Authorization'] = f'Bearer {token}'
            self.last_token_fetch = datetime.now()
            self.requests_count = 0

    def _connect(self):
        if not self._username or not self._password is not None:
            raise RESTException('No user name or API key')
        try:
            self.refresh_access_token(force=True)  # just try
            self._got_token = True
            logger.info('oauth success')
        except Exception:
            logger.exception('Oauth failed')
            self._got_token = False
        self._get('devices/queries/devices/v1',
                  do_basic_auth=not self._got_token,
                  url_params={'limit': consts.DEVICES_PER_PAGE, 'offset': 0})

    def get_devices_data(self, devices_ids):
        retries = 0
        if len(devices_ids) > consts.MAX_DEVICES_PER_PAGE:
            logger.warning(f'Request too many devices_ids: {devices_ids}, max: {consts.MAX_DEVICES_PER_PAGE}')
        while retries < consts.REQUEST_RETRIES:
            try:
                return self._get('devices/entities/devices/v1',
                                 url_params={'ids': devices_ids},
                                 do_basic_auth=not self._got_token)
            except RESTRequestException as e:
                logger.error(f'Error getting devices data: {e}')
                time.sleep(consts.RETRIES_SLEEP_TIME)
                self.refresh_access_token()
                retries += 1
                if retries >= consts.REQUEST_RETRIES:
                    raise e

    def get_devices_ids(self, offset, devices_per_page):
        retries = 0
        logger.debug(f'Getting devices offset {offset}, devices per page: {devices_per_page}')
        while retries < consts.REQUEST_RETRIES:
            try:
                return self._get('devices/queries/devices/v1',
                                 url_params={'limit': devices_per_page, 'offset': offset},
                                 do_basic_auth=not self._got_token)
            except RESTRequestException as e:
                logger.error(f'Error getting devices ids: {e}')
                time.sleep(consts.RETRIES_SLEEP_TIME)
                self.refresh_access_token()
                retries += 1
                if retries >= consts.REQUEST_RETRIES:
                    raise e

    # pylint: disable=arguments-differ

    def get_device_list(self):
        offset = 0
        devices_per_page = consts.DEVICES_PER_PAGE
        try:
            response = self.get_devices_ids(offset, devices_per_page)
            offset += devices_per_page
            self.requests_count += 1
            total_count = response['meta']['pagination']['total']
        except Exception:
            logger.exception(f'Cant get total count')
            raise RESTException('Cant get total count')
        devices_per_page = int(consts.DEVICES_PER_PAGE_PERCENTAGE / 100 * total_count)
        # check if devices_per_page is not too big or too small
        if devices_per_page > consts.MAX_DEVICES_PER_PAGE:
            devices_per_page = consts.MAX_DEVICES_PER_PAGE
        if devices_per_page < consts.DEVICES_PER_PAGE:
            devices_per_page = consts.DEVICES_PER_PAGE

        devices = self.get_devices_data(response['resources'])
        yield from devices['resources']
        while offset < total_count and offset < consts.MAX_NUMBER_OF_DEVICES:
            try:
                response = self.get_devices_ids(offset, devices_per_page)
                devices = self.get_devices_data(response['resources'])
                yield from devices['resources']
                self.requests_count += 2
                if self._got_token and self.requests_count >= consts.REFRESH_TOKEN_REQUESTS:
                    self.refresh_access_token()
            except Exception:
                logger.exception(f'Problem getting offset {offset}')
            offset += devices_per_page
