import logging
import time
from datetime import datetime, timedelta
from functools import partialmethod
from typing import Optional, Tuple, Generator

import requests  # pylint: disable=unused-import
from retrying import retry
from urllib3.util import parse_url

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from sumo_logic_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class SumoLogicRetryException(Exception):
    """ Exception used to mark an HTTP Error of code 429 """


class SumoLogicConnection(RESTConnection):
    """ rest client for SumoLogic adapter """

    def __init__(self, *args, access_id: str, access_key: str, search_query: str, **kwargs):
        super().__init__(*args, url_base_prefix='/api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._access_id = access_id
        self._access_key = access_key
        self._search_query = search_query

    def _connect(self):
        if not (self._access_id and self._access_key and self._search_query):
            raise RESTException('No Access ID or Access Key or Search Query')

        # Adjust url to the api sub domain, see:
        # https://help.sumologic.com/APIs/General-API-Information/Sumo-Logic-Endpoints-and-Firewall-Security
        api_url = consts.DOMAIN_RE.sub(consts.DOMAIN_TO_API_RE_REPLACE, self._url)
        if not api_url.startswith(consts.DOMAIN_API_URL_PREFIX):
            logger.info(f'Invalid api url generated "{api_url}" from url "{self._url}"')
            raise RESTException('Invalid domain given, Must be your service endpoint (login URL),'
                                ' similar to https://service.sumologic.com or https://service.eu.sumologic.com'
                                ' (where "eu." is according to your specific SumoLogic service endpoint.)')
        self._url = str(parse_url(api_url))

        # perform a quick search (1 second time frame) to see that the search is valid and we are permitted to do it.
        # raise in case an error returned
        _ = list(self._iter_search_raise_errors(earliest=datetime.utcnow() - timedelta(seconds=1),
                                                latest=datetime.utcnow(),
                                                sample_rate_secs=1))

    # pylint: disable=arguments-differ
    @retry(stop_max_attempt_number=3,
           retry_on_exception=lambda exc: isinstance(exc, SumoLogicRetryException))
    def _do_request(self, *args, **kwargs):
        # use basic auth if not instructed otherwise
        if kwargs.setdefault('do_basic_auth', True):
            kwargs.setdefault('alternative_auth_dict', (self._access_id, self._access_key))
        return super()._do_request(*args, **kwargs)

    # pylint: disable=arguments-differ
    def _handle_response(self, response, *args, **kwargs):
        if response.status_code == 429:
            raise SumoLogicRetryException()
        return super()._handle_response(response, *args, **kwargs)

    def _paginated_request(self, *args, total_count: int, pagination_field: str, **kwargs):

        body_params = kwargs.setdefault(
            'url_params' if (kwargs.get('method') or args[0]) == 'GET'
            else 'body_params', {})
        body_params.setdefault(consts.PAGINATION_PER_PAGE_FIELD, consts.DEVICE_PER_PAGE)
        curr_offset = body_params.setdefault(consts.PAGINATION_OFFSET_FIELD, 0)
        # Note: initial value used only for initial while iteration
        try:
            while curr_offset <= total_count:
                body_params[consts.PAGINATION_OFFSET_FIELD] = curr_offset
                response = self._do_request(*args, **kwargs)

                pagination_value = response.get(pagination_field)
                if not isinstance(pagination_value, list):
                    logger.error(f'Invalid "{pagination_field}" found on {curr_offset}/{total_count}'
                                 f' in response: {response}')
                    return

                curr_count = len(pagination_value)
                if curr_count == 0:
                    logger.debug(f'No "{pagination_field}" found on {curr_offset}/{total_count}. Halting..')
                    return

                logger.info(f'Yielding {curr_count}/{total_count} "{pagination_field}"')
                yield from pagination_value

                curr_offset += curr_count
        except Exception:
            logger.exception(f'Failed paginated request after {curr_offset}/{total_count}')

    _paginated_get = partialmethod(_paginated_request, 'GET')

    def _get_search_job_status(self, job_id: str):
        return self._get(f'{consts.ENDPOINT_SEARCH_JOBS}/{job_id}')

    def _wait_for_search_job(self, job_id: str, sample_rate_secs=5) -> Optional[Tuple[dict, list, list]]:
        """ return last search status """
        errors = []
        warnings = []

        last_notice = start_time = datetime.utcnow()
        while True:

            # assert time execution
            now = datetime.utcnow()
            execution_time = now - start_time
            if execution_time > consts.MAX_WAIT_SEARCH_JOB:
                raise RESTException(f'Search job {job_id} took more than {consts.MAX_WAIT_SEARCH_JOB} hours.'
                                    f' Errors:{errors}, Warnings:{warnings}')
            if now - last_notice > consts.EXECUTION_NOTICE_PERIOD:
                logger.warning(f'Search job {job_id} is already running for {execution_time}.')
                last_notice = datetime.utcnow()

            job_status_response = self._get_search_job_status(job_id)
            job_state = job_status_response.get('state')
            job_message_count = job_status_response.get('messageCount')

            pending_errors = job_status_response.get('pendingErrors')
            if isinstance(pending_errors, list):
                for error in pending_errors:
                    logger.error(f'Search job {job_id} error after {job_message_count} messages on state {job_state}:'
                                 f' {error}')
                    errors.append(error)

            pending_warnings = job_status_response.get('pendingWarnings')
            if isinstance(pending_warnings, list):
                for warning in pending_warnings:
                    logger.warning(f'Search job {job_id} warning after {job_message_count} messages'
                                   f' on state {job_state}: {warning}')
                    warnings.append(warning)

            if job_state not in consts.SEARCH_JOB_STATES:
                message = f'Unknown job state found: {job_state}'
                logger.debug(f'{message} in status response: {job_status_response}')
                raise RESTException(message)

            if job_state not in consts.SEARCH_JOB_EXIT_STATES:
                # if job didn't finish yet, wait 5 secs and try again
                logger.debug(f'search job {job_id} status={job_state}, sleeping {sample_rate_secs} seconds')
                time.sleep(sample_rate_secs)
                continue

            elif job_state == consts.STATUS_SEARCH_JOB_CANCELLED:
                logger.info(f'Search canceled after {job_message_count} messages. Halting..')
                return None

            return job_status_response, errors, warnings

    def _create_search_job(self, earliest: datetime, latest: Optional[datetime] = None):
        # prepare params
        latest = latest or datetime.utcnow()

        # prepare datetime formattings
        earliest = earliest.strftime(consts.SEARCH_QUERY_DT_FORMATS)
        latest = latest.strftime(consts.SEARCH_QUERY_DT_FORMATS)

        logger.info(f'running search "{self._search_query}"'
                    f' from {earliest} to {latest}')

        # create search
        response = self._post(consts.ENDPOINT_SEARCH_JOBS,
                              use_json_in_response=False,
                              return_response_raw=True,
                              body_params={
                                  'query': self._search_query,
                                  'from': earliest,
                                  'to': latest,
                                  'timeZone': 'UTC',
                              })  # type: requests.Response

        try:
            # Note: response location is in the following format:
            #   https://api.sumologic.com/api/v1/search/jobs/SEARCH_JOB_ID
            return response.headers['Location'].rstrip('/').rsplit('/', 1)[-1]
        except Exception:
            logger.exception(f'Invalid job id found in response headers {response.headers}.')
            raise RESTException(f'Invalid Job Id retrieved by SumoLogic. please contact Axonius support.')

    def _iter_search_raise_errors(self, earliest: datetime, latest: Optional[datetime] = None,
                                  limit: int = consts.MAX_NUMBER_OF_DEVICES, sample_rate_secs=5):
        errors, _ = (yield from self.iter_search(earliest=earliest, latest=latest, limit=limit,
                                                 sample_rate_secs=sample_rate_secs))
        if isinstance(errors, list) and errors:
            raise RESTException(f'SumoLogic search query errors: {errors}')

    def iter_search(self, earliest: datetime, latest: Optional[datetime] = None,
                    limit: int = consts.MAX_NUMBER_OF_DEVICES, sample_rate_secs=5) \
            -> Generator[dict, None, Tuple[list, list]]:

        job_id = self._create_search_job(earliest=earliest, latest=latest)
        search_job_res = self._wait_for_search_job(job_id, sample_rate_secs=sample_rate_secs)
        if not (isinstance(search_job_res, tuple) and len(search_job_res) == 3):
            logger.warning('No Search job result returned.')
            raise RESTException('No Search job result returned')

        last_status, errors, warnings = search_job_res
        message_count = (last_status or {}).get('messageCount')
        if not isinstance(message_count, int):
            message = 'no messageCount returned'
            logger.error(f'{message} for last_status: {last_status}')
            raise RESTException(message)

        for message_dict in self._paginated_get(f'{consts.ENDPOINT_SEARCH_JOBS}/{job_id}/messages',
                                                total_count=min(message_count, limit),
                                                pagination_field='messages'):
            message_map = message_dict.get('map')
            if not isinstance(message_map, dict):
                continue
            yield message_map
        return errors, warnings

    # pylint: disable=arguments-differ
    def get_device_list(self, max_log_history: int, maximum_records: int):
        start_timestamp = datetime.utcnow() - timedelta(days=max_log_history)
        yield from self.iter_search(earliest=start_timestamp, limit=maximum_records)
