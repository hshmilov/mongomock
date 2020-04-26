import logging
import time
from datetime import datetime, timedelta
from itertools import repeat
from typing import Optional, Tuple, Generator, Dict

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

    def _paginated_get(self, *args, total_count: int, pagination_field: str, repeated_field: Optional[str] = None,
                       **kwargs) -> Generator[Tuple[dict, Optional[dict]], None, None]:

        request_params = kwargs.setdefault('url_params', {})
        request_params.setdefault(consts.PAGINATION_PER_PAGE_FIELD, consts.DEVICE_PER_PAGE)
        curr_offset = request_params.setdefault(consts.PAGINATION_OFFSET_FIELD, 0)
        count_so_far = 0
        # Note: initial value used only for initial while iteration
        try:
            while curr_offset <= total_count:
                request_params[consts.PAGINATION_OFFSET_FIELD] = curr_offset
                response = self._get(*args, **kwargs)

                pagination_value = response.get(pagination_field)
                if not isinstance(pagination_value, list):
                    logger.error(f'Invalid "{pagination_field}" found on {curr_offset} ({count_so_far}/{total_count})'
                                 f' in response: {response}')
                    return

                curr_count = len(pagination_value)
                if curr_count == 0:
                    logger.debug(f'No "{pagination_field}" found on {curr_offset} ({count_so_far}/{total_count}).'
                                 f' Halting..')
                    return
                count_so_far += curr_count
                repeated_value = response.get(repeated_field)

                logger.info(f'Yielding {curr_count} "{pagination_field}" ({count_so_far}/{total_count})')
                yield from zip(pagination_value, repeat(repeated_value))

                curr_offset += curr_count
        except Exception:
            logger.exception(f'Failed paginated request on {curr_offset} ({count_so_far}/{total_count})')

    def _get_search_job_status(self, job_id: str):
        return self._get(f'{consts.ENDPOINT_SEARCH_JOBS}/{job_id}')

    def _wait_for_search_job(self, job_id: str, sample_rate_secs=5) -> Optional[Tuple[dict, list, list]]:
        """ return last search status """
        errors = []
        warnings = []

        last_notice = start_time = datetime.utcnow()
        exceed_max_wait = False
        while not exceed_max_wait:

            job_status_response = self._get_search_job_status(job_id)

            # assert time execution
            now = datetime.utcnow()
            execution_time = now - start_time
            if execution_time > consts.MAX_WAIT_SEARCH_JOB:
                exceed_max_wait = True
                continue
            if now - last_notice > consts.EXECUTION_NOTICE_PERIOD:
                logger.warning(f'Search job {job_id} is already running for {execution_time}.')
                last_notice = datetime.utcnow()

            job_state = job_status_response.get('state')
            job_message_count = job_status_response.get('messageCount')
            job_record_count = job_status_response.get('recordCount')

            pending_errors = job_status_response.get('pendingErrors')
            if isinstance(pending_errors, list):
                for error in pending_errors:
                    logger.error(f'Search job {job_id} error after {execution_time}, {job_message_count} messages '
                                 f'and {job_record_count} records on state {job_state}: {error}')
                    errors.append(error)

            pending_warnings = job_status_response.get('pendingWarnings')
            if isinstance(pending_warnings, list):
                for warning in pending_warnings:
                    logger.warning(f'Search job {job_id} warning after {execution_time}, {job_message_count} messages'
                                   f' and {job_record_count} records on state {job_state}: {warning}')
                    warnings.append(warning)

            if job_state not in consts.SEARCH_JOB_STATES:
                message = f'Unknown job state found: {job_state}'
                logger.debug(f'{message} after {execution_time} in status response: {job_status_response}')
                raise RESTException(message)

            if job_state not in consts.SEARCH_JOB_EXIT_STATES:
                # if job didn't finish yet, wait 5 secs and try again
                logger.debug(f'search job {job_id} status={job_state}, sleeping {sample_rate_secs} seconds')
                time.sleep(sample_rate_secs)
                continue

            elif job_state == consts.STATUS_SEARCH_JOB_CANCELLED:
                logger.info(f'Search canceled after {execution_time} and {job_message_count} messages. Halting..')
                return None

            logger.info(f'Search Done in {execution_time} after {job_message_count} messages'
                        f' and {job_record_count} records.')
            return job_status_response, errors, warnings

        raise RESTException(f'Search job {job_id} took more than {consts.MAX_WAIT_SEARCH_JOB} hours.'
                            f' Errors:{errors}, Warnings:{warnings}')

    def _create_search_job(self, earliest: datetime, latest: Optional[datetime] = None):
        # prepare params
        latest = latest or datetime.utcnow()
        if earliest > latest:
            raise ValueError('Requested earliest {earliest} is after latest {latest}')

        # prepare datetime formattings
        earliest = earliest.strftime(consts.SEARCH_QUERY_DT_FORMATS)
        latest = latest.strftime(consts.SEARCH_QUERY_DT_FORMATS)

        logger.info(f'running search "{self._search_query}"'
                    f' from {earliest} to {latest}')

        # create search
        body_params = {'query': self._search_query,
                       'from': earliest,
                       'to': latest,
                       'timeZone': 'UTC'}
        response = self._post(consts.ENDPOINT_SEARCH_JOBS,
                              use_json_in_response=False,
                              return_response_raw=True,
                              body_params=body_params)  # type: requests.Response

        try:
            # Note: response location is in the following format:
            #   https://api.sumologic.com/api/v1/search/jobs/SEARCH_JOB_ID
            return response.headers['Location'].rstrip('/').rsplit('/', 1)[-1]
        except Exception:
            logger.exception(f'Invalid job id found in response headers {response.headers}.')
            raise RESTException(f'Invalid Job Id retrieved by SumoLogic. please contact Axonius support.')

    def _iter_search_raise_errors(self, earliest: datetime,
                                  latest: Optional[datetime] = None,
                                  limit: int = consts.MAX_NUMBER_OF_DEVICES,
                                  sample_rate_secs=5):
        errors, _ = (yield from self.iter_search(earliest=earliest, latest=latest, limit=limit,
                                                 sample_rate_secs=sample_rate_secs))
        if errors and isinstance(errors, list):
            raise RESTException(f'SumoLogic search query errors ({len(errors)}: {errors}')

    def _iter_result_records_for_job(self, job_id_url, last_status: dict, limit: int = consts.MAX_NUMBER_OF_DEVICES):
        record_count = (last_status or {}).get('recordCount')
        if not (isinstance(record_count, int) and record_count > 0):
            logger.warning(f'invalid record_count found in last_status {last_status}')
            return
        for record_dict, _ in self._paginated_get(f'{job_id_url}/records',
                                                  total_count=min(limit, record_count),
                                                  pagination_field='records'):
            if not (isinstance(record_dict, dict) and isinstance(record_dict.get('map'), dict)):
                logger.warning(f'Invalid record_dict returned: {record_dict}')
                continue

            yield record_dict['map']

    @staticmethod
    def _is_key_field_dict(field_dict):
        return isinstance(field_dict, dict) and bool(field_dict.get('keyField'))

    def _map_records_for_job(self, job_id_url: str, record_count: int) \
            -> Dict[Tuple, dict]:
        """
            :return { record_key_field_tuple: { record_key_values_tuple: record_dict } }
                    e.g. {('hostname','ip'): {('testHost','127.0.0.1'): record}}
        """

        records_by_key_field_and_values = {}
        for record_dict, record_fields in self._paginated_get(f'{job_id_url}/records',
                                                              total_count=record_count,
                                                              pagination_field='records',
                                                              repeated_field='fields'):
            if not (isinstance(record_dict, dict) and isinstance(record_fields, list)):
                logger.warning(f'Invalid record or fields received. fields: {record_fields} , record: {record_dict}')
                continue
            if not isinstance(record_dict.get('map'), dict):
                logger.warning(f'Invalid map found in record: {record_dict}')
                continue

            # compute record key fields, i.e. has item 'keyField': True
            record_key_fields = filter(self._is_key_field_dict, record_fields)
            # Note: we sort the record field names so we can later perform tuple comparisons:
            #       e.g. ('a','b')==('b','a') is False but in the correct order its True.
            record_key_field_names = tuple(sorted(key_field.get('name') for key_field in record_key_fields))

            record_map = record_dict['map']
            record_key_values = tuple(record_map.get(k) for k in record_key_field_names)

            # Note: this only inserts record_dict if the key_fields and key_values combination was not inserted yet.
            #       in this case, the original inserted dict would be returned and warned.
            records = records_by_key_field_and_values.setdefault(record_key_field_names, {})
            first_inserted_dict = records.setdefault(record_key_values, record_map)
            if first_inserted_dict != record_map:
                logger.warning(f'record duplicity encountered: {record_map} {first_inserted_dict}')

        return records_by_key_field_and_values

    def _iter_result_messages_for_job(self, job_id_url, message_count: int):
        # Note: we dont use repeated_field so we may just ignore the second value
        for message_dict, _ in self._paginated_get(f'{job_id_url}/messages',
                                                   total_count=message_count,
                                                   pagination_field='messages'):
            if not (isinstance(message_dict, dict) and isinstance(message_dict.get('map'), dict)):
                logger.warning(f'Invalid message returned: {message_dict}')

            yield message_dict['map']

    def _iter_combined_results_for_job(self, job_id_url, last_status, limit: int = consts.MAX_NUMBER_OF_DEVICES):

        message_count = (last_status or {}).get('messageCount')
        if not isinstance(message_count, int):
            message = 'no messageCount returned'
            logger.error(f'{message} for last_status: {last_status}')
            raise RESTException(message)
        messages_iter = self._iter_result_messages_for_job(job_id_url, min(limit, message_count))

        # records are not required to be returned
        record_count = (last_status or {}).get('recordCount') or 0
        records_by_key_fields_and_values = \
            self._map_records_for_job(job_id_url, min(limit, record_count))
        if len(records_by_key_fields_and_values) > consts.RECORD_WARNING_THRESHOLD:
            logger.warning(f'More than {consts.RECORD_WARNING_THRESHOLD} record types found')

        # stitch message and records
        for message_dict in messages_iter:
            message_map = message_dict.get('map')
            if not isinstance(message_map, dict):
                continue

            # for every record type
            for record_key_fields, record_by_key_values in records_by_key_fields_and_values.items():

                # locate matching record according to the message key fields' values in order to stitch them together
                message_key_values = tuple(message_map.get(k) for k in record_key_fields)
                matching_record_map = None
                for record_key_values, record_map in record_by_key_values.items():
                    if record_key_values == message_key_values:
                        matching_record_map = record_map
                        break
                if not isinstance(matching_record_map, dict):
                    continue

                # stitch message with its matching record (message values override record values)
                message_map = {**matching_record_map, **message_map}

            yield message_map

    def iter_search(self, earliest: datetime, latest: Optional[datetime] = None,
                    limit: int = consts.MAX_NUMBER_OF_DEVICES, sample_rate_secs=5,
                    include_messages: bool=False) \
            -> Generator[dict, None, Tuple[list, list]]:
        errors = []
        warnings = []
        job_id = self._create_search_job(earliest=earliest, latest=latest)
        if not job_id:
            logger.warning(f'no job_id returned: {job_id}')
            # return empty errors and warnings
            return errors, warnings

        search_job_res = self._wait_for_search_job(job_id, sample_rate_secs=sample_rate_secs)
        if not (isinstance(search_job_res, tuple) and len(search_job_res) == 3):
            logger.warning('No Search job result returned.')
            raise RESTException('No Search job result returned')
        last_status, errors, warnings = search_job_res

        job_id_url = f'{consts.ENDPOINT_SEARCH_JOBS}/{job_id}'
        if not include_messages:
            yield from self._iter_result_records_for_job(job_id_url, last_status, limit=limit)
        else:
            yield from self._iter_combined_results_for_job(job_id_url, last_status, limit=limit)

        return errors, warnings

    # pylint: disable=arguments-differ
    def get_device_list(self, max_log_history: int, maximum_records: int, include_messages: bool = False):
        start_timestamp = datetime.utcnow() - timedelta(days=max_log_history)
        yield from self.iter_search(earliest=start_timestamp, limit=maximum_records,
                                    include_messages=include_messages)
