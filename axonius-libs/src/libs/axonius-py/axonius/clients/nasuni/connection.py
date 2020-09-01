import logging
import datetime
import time

from axonius.clients.rest.connection import RESTConnection, DEFAULT_429_SLEEP_TIME
from axonius.clients.rest.exception import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import int_or_none
from axonius.clients.nasuni.consts import API_URL_BASE_PREFIX, API_URL_AUTH_SUFFIX, TOKEN_DEFAULT_EXPIRATION_TIME_SEC, \
    API_URL_FILERS_SUFFIX, DEVICE_PER_PAGE, MAX_NUMBER_OF_FILERS

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class NasuniConnection(RESTConnection):
    """ rest client for Nasuni adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=API_URL_BASE_PREFIX,
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
                'username': self._username,
                'password': self._password
            }
            response = self._post(API_URL_AUTH_SUFFIX, body_params=body_params)
            if not (isinstance(response, dict) and response.get('token')):
                raise RESTException(f'Failed getting token, received invalid response: {response}')

            # Due to lack of documentation, try parsing expires with both datetime and int
            expires = parse_date(response.get('expires'))
            if isinstance(expires, datetime.datetime) and expires:
                if datetime.datetime.now() > expires:
                    message = f'Received invalid token expire time {response}'
                    logger.warning(message)
                    raise RESTException(message)
                expires = (expires - datetime.datetime.now()).seconds
            else:
                expires = int_or_none(response.get('expires')) or TOKEN_DEFAULT_EXPIRATION_TIME_SEC
            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=(expires - 50))

            self._token = response.get('token')
            self._session_headers['Authorization'] = self._token

        except RESTException as e:
            raise RESTException(f'Error: Could not login to the server, please check domain or credentials. {str(e)}')

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            self._get_token()

            url_params = {
                'offset': 0,  # Starting position
                'limit': 1  # Max number of items
            }
            self._get(API_URL_FILERS_SUFFIX, url_params=url_params)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        """
        Overrides _do_request from RestConnection.
        Do request with the parameters and in case of '429' error wait and retry.
        '429' error means that too many requests made in a short time and we need to wait X seconds before
        trying to send the next request.
        """
        # Default values of original _do_request
        raise_for_status = kwargs.pop('raise_for_status', True)
        use_json_in_response = kwargs.pop('use_json_in_response', True)
        return_response_raw = kwargs.pop('return_response_raw', False)
        resp_raw = super()._do_request(
            *args,
            raise_for_status=False,
            use_json_in_response=False,
            return_response_raw=True,
            **kwargs
        )
        if resp_raw.status_code == 429:
            try:
                retry_after = resp_raw.headers.get('Retry-After') or resp_raw.headers.get('retry-after')
                if retry_after:
                    logger.info(f'Got 429, sleeping for {retry_after}')
                else:
                    logger.info(f'Got 429 with no retry-after header, sleeping for {DEFAULT_429_SLEEP_TIME}')
                    retry_after = DEFAULT_429_SLEEP_TIME
                time.sleep(int(retry_after) + 1)
            except Exception:
                time.sleep(DEFAULT_429_SLEEP_TIME)
            return super()._do_request(*args,
                                       raise_for_status=raise_for_status,
                                       use_json_in_response=use_json_in_response,
                                       return_response_raw=return_response_raw,
                                       **kwargs)

        return self._handle_response(resp_raw,
                                     raise_for_status=raise_for_status,
                                     use_json_in_response=use_json_in_response,
                                     return_response_raw=return_response_raw)

    def _paginated_filers_get(self):
        try:
            total_fetched_filers = 0

            url_params = {
                'offset': 0,
                'limit': 1
            }
            total_filers = MAX_NUMBER_OF_FILERS
            self._refresh_token()
            response = self._get(API_URL_FILERS_SUFFIX, url_params=url_params)
            if isinstance(response, dict) and int_or_none(response.get('total')):
                total_filers = min(int_or_none(response.get('total')), MAX_NUMBER_OF_FILERS)

            url_params['limit'] = DEVICE_PER_PAGE
            while url_params['offset'] < total_filers:
                self._refresh_token()
                response = self._get(API_URL_FILERS_SUFFIX, url_params=url_params)
                if not (isinstance(response, dict) and isinstance(response.get('items'), list)):
                    logger.warning(f'Received invalid response for filers: {response}')
                    continue

                for filer in response.get('items'):
                    if isinstance(filer, dict):
                        yield filer
                        total_fetched_filers += 1

                if total_fetched_filers >= total_filers:
                    logger.info('Exceeded max number of filers.')
                    break

                if len(response.get('items')) < DEVICE_PER_PAGE:
                    logger.info(f'Done filers pagination, last page got '
                                f'{len(response.get("items"))} / {DEVICE_PER_PAGE}')
                    break

                url_params['offset'] += DEVICE_PER_PAGE

            logger.info(f'Got total of {total_fetched_filers} filers, out of max {total_filers}')
        except Exception:
            logger.exception(f'Invalid request made while paginating filers')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_filers_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
