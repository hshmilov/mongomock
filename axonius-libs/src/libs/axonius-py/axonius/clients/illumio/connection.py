import logging
import time
import requests

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.illumio.consts import BASE_ENDPOINT, MAX_ITERATIONS, \
    ASYNC_DEVICE_TRIGGER, ASYNC_JOB_STATUS_FINISHED, ASYNC_DEFAULT_RETRY_AFTER, \
    ASYNC_DEVICE_LIMIT, ASYNC_EXTRA_HEADERS, DEVICE_ENDPOINT, \
    RULESET_ENDPOINT, RULESET_STATUS, SUCCESS_CODES, ASYNC_JOB_STATUS_DONE, \
    ASYNC_JOB_STATUS_FAILED, DEVICE_TYPE
from axonius.utils.parsing import int_or_none

logger = logging.getLogger(f'axonius.{__name__}')


class IllumioConnection(RESTConnection):
    """ rest client for Illumio adapter """

    def __init__(self, org_id: str, *args, **kwargs):
        super().__init__(*args, url_base_prefix=BASE_ENDPOINT,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._session_refresh = None
        self._org_id = int_or_none(org_id)

        # endpoints for discovery
        self._device_endpoint = f'{DEVICE_ENDPOINT}'.format(org_id=org_id)
        self._ruleset_endpoint = f'{RULESET_ENDPOINT}'.format(org_id=org_id, status=RULESET_STATUS)

        # documentation is unclear on the auth mechanism, so including the token
        self._apikey = self._password

    def _connect(self):
        if not (self._username and self._password and self._org_id):
            raise RESTException(f'Complete authentication parameters were not '
                                f'supplied. Authentication Username, Secret and '
                                f'Organization ID are required.')

        try:
            self._session_headers['Authorization'] = f'Token token={self._apikey}'
            self._get(self._device_endpoint,
                      do_basic_auth=True,
                      url_params={'max_results': 1}
                      )
        except Exception as err:
            raise ValueError(f'Error: Invalid response from server, please '
                             f'check domain, port or credentials. {str(err)}')

    # pylint: disable=too-many-branches, too-many-statements
    def get_device_list(self):
        """
        The API allows for a GET on 500 items or less. If there are more
        than 500, the API forces the caller into using an asynchronous
        get/wait/fetch model.

        NOTES:
            I am unsure about the data returned, so I have some debug
                statements in here that can be removed in the future.

            https://docs.illumio.com/asp/20.1/Content/Guides/rest-api/async-get-collections/async-job-operations.htm
            https://docs.illumio.com/asp/20.1/API-Reference/index.html#get-workloads
        """
        try:
            # see how many VEN items will be returned from this query
            try:
                total_items = self._get_total_items(
                    endpoint=self._device_endpoint,
                    limit=1
                )
                logger.debug(f'Found {total_items} {DEVICE_TYPE.get("ven")}')
            except Exception as err:
                logger.exception(f'{DEVICE_TYPE.get("ven")} item count fetch '
                                 f'failed: {str(err)}')
                raise

            # single-call GET for small numbers of items
            if total_items <= ASYNC_DEVICE_LIMIT:
                logger.debug(f'Using sync GET to fetch {total_items} devices')
                try:
                    vens = self._get(self._device_endpoint, do_basic_auth=True)
                    logger.info(f'Found {len(vens)} of {total_items} '
                                f'{DEVICE_TYPE.get("ven")}')
                except Exception as err:
                    logger.exception(f'Unable to synchronously fetch {total_items} '
                                     f'{DEVICE_TYPE.get("ven")} from '
                                     f'{self._device_endpoint}: {str(err)}')
                    raise
            # long and painful async GET
            else:
                logger.debug(f'Using async GET to fetch {total_items} devices')
                try:
                    vens = self._get_items_async(endpoint=self._device_endpoint,
                                                 device_type=DEVICE_TYPE.get('ven'))
                    logger.info(f'Found {len(vens)} of {total_items} '
                                f'{DEVICE_TYPE.get("ven")}')
                except RESTException as err:
                    logger.exception(str(err))
                    raise

            if not isinstance(vens, list):
                message = f'Malformed devices data returned from ' \
                          '{self._device_endpoint}. Expected a list, ' \
                          f'got {type(vens)}: {str(vens)}'
                logger.warning(message)
                raise ValueError(message)

            # see how many ruleset items will be returned from this query
            try:
                total_items = self._get_total_items(
                    endpoint=self._ruleset_endpoint,
                    limit=1
                )
                logger.debug(f'Found {total_items} {DEVICE_TYPE.get("rule")}')
            except Exception as err:
                logger.exception(f'Ruleset item count fetch failed: {str(err)}')
                raise

            # single-call GET for small numbers of rulesets
            if total_items <= ASYNC_DEVICE_LIMIT:
                logger.debug(f'Using sync GET to fetch {total_items} '
                             f'{DEVICE_TYPE.get("rule")}')
                try:
                    rulesets = self._get(self._ruleset_endpoint, do_basic_auth=True)
                    logger.info(f'Found {len(rulesets)} of {total_items} '
                                f'{DEVICE_TYPE.get("rule")}')
                except Exception as err:
                    logger.exception(
                        f'Unable to synchronously fetch {total_items} '
                        f'{DEVICE_TYPE.get("rule")} from {self._ruleset_endpoint}: '
                        f'{str(err)}')
                    raise
            # long and painful async GET for rulesets
            else:
                logger.debug(f'Using async GET to fetch {total_items} '
                             f'{DEVICE_TYPE.get("rule")}')
                try:
                    rulesets = self._get_items_async(
                        endpoint=self._ruleset_endpoint,
                        device_type=DEVICE_TYPE.get('rule')
                    )
                    logger.info(f'Found {len(rulesets)} of {total_items} '
                                f'{DEVICE_TYPE.get("rule")}')
                except RESTException as err:
                    logger.exception(str(err))
                    raise

            if not isinstance(rulesets, list):
                message = f'Malformed devices data returned from ' \
                          f'{self._ruleset_endpoint}. Expected a list, ' \
                          f'got {type(rulesets)}: {str(rulesets)}'
                logger.warning(message)
                raise ValueError(message)

            for ven in vens:
                yield ven, rulesets

        except Exception as err:
            logger.exception(f'Unable to fetch data from Illumio')

    # pylint: disable=too-many-nested-blocks, too-many-branches,
    # pylint: disable=invalid-triple-quote, too-many-statements
    def _wait_for_job(self, response) -> list:
        """
        NOTE: I'm making a HUGE assumption here that the returned data is
                a list. The docs don't really define this well.

        :param response: A requests.response object
        :return: A list of dicts containing the data
        """
        status = 'running'
        iterations_counter = 1

        while status not in ASYNC_JOB_STATUS_FINISHED:
            if iterations_counter >= MAX_ITERATIONS:
                logger.warning(f'Async job exceeded the maximum number of '
                               f'{MAX_ITERATIONS} iterations')
                return None

            response_headers = response.headers
            if isinstance(response_headers,
                          (dict, requests.structures.CaseInsensitiveDict)
                          ):
                # set the URI to poll for job status
                job_location = self._get_location(headers=response_headers)
                if not isinstance(job_location, str):
                    message = f'Malformed job location URI. Expected a ' \
                              f'string, got {type(job_location)}: ' \
                              f'{str(job_location)}'
                    logger.warning(message)
                    raise ValueError(message)

                # set the minimum retry time
                retry_after = self._get_retry_after(headers=response_headers)
                if not isinstance(retry_after, int):
                    logger.warning(f'Malformed retry after value. Expected an '
                                   f'int, got {type(retry_after)}: '
                                   f'{str(retry_after)}')
                    retry_after = ASYNC_DEFAULT_RETRY_AFTER

                # set the current job status
                status = self._get_status(headers=response_headers)
                if not isinstance(status, str):
                    message = f'Malformed job status. Expected a ' \
                              f'string, got {type(status)}: ' \
                              f'{str(status)}'
                    logger.warning(message)
                    raise ValueError(message)

                logger.debug(f'Waiting {retry_after} seconds for {status}. '
                             f'Job status is at {job_location}: '
                             f'Iteration {iterations_counter}')

                time.sleep(int_or_none(retry_after))
                try:
                    job_status_response = self._get(job_location, do_basic_auth=True)
                    if not isinstance(job_status_response, dict):
                        message = f'Malformed job status response. Expected a ' \
                                  f'dict, got {type(job_status_response)}:' \
                                  f'{str(job_status_response)}'
                        logger.warning(message)
                        raise ValueError(message)

                    status = job_status_response.get('status')
                    if not isinstance(status, str):
                        message = f'Malformed job status. Expected a string, ' \
                                  f'got {type(status)}: {str(status)}'
                        logger.warning(message)
                        raise ValueError(message)

                    if status == ASYNC_JOB_STATUS_DONE:
                        # this is a potential issue, since there is no example
                        # in the docs about this HREF (is it relative or
                        # absolute?)
                        result = job_status_response.get('result')
                        if not isinstance(result, dict):
                            message = f'Malformed job status result response. Expected ' \
                                      f'a dict, got {type(result)}: {str(result)}'
                            logger.warning(message)
                            raise ValueError(message)

                        data_fetch_url = result.get('href')
                        if not (isinstance(data_fetch_url, str) and data_fetch_url):
                            message = f'Malformed job status response. Expected ' \
                                      f'a string, got {type(data_fetch_url)}: ' \
                                      f'{str(data_fetch_url)}'
                            logger.warning(message)
                            raise ValueError(message)

                        if data_fetch_url.startswith('/'):
                            data_fetch_url = data_fetch_url[1:]

                        try:
                            return self._get(data_fetch_url, do_basic_auth=True)
                        except Exception as err:
                            logger.exception(
                                f'Unable to fetch data from async job: '
                                f'{str(err)}')
                            raise
                    elif status == ASYNC_JOB_STATUS_FAILED:
                        message = f'Async job failed: {job_status_response}'
                        logger.warning(message)
                        raise ValueError(message)
                except requests.HTTPError as e:
                    self._handle_http_error(e)
            else:
                message = f'Malformed response headers in job status ' \
                          f'fetch. Expected a dict-like object, got ' \
                          f'{type(response_headers)}: ' \
                          f'{str(response_headers)}'
                logger.warning(message)
                raise ValueError(f'Unable to fetch devices: {str(message)}')

            iterations_counter += 1

    @staticmethod
    def _get_location(headers: dict) -> str:
        """
        Retrieve the HREF location of the job or job results from the
        response headers and return it to the caller.

        :param headers: API response headers as a dict
        :return location: An HREF showing the location of a job or the
        job results
        """
        # docs are inconsistent about the header names
        # location comes in the form of /orgs/#/jobs/href
        location = headers.get('Location') or headers.get('location')

        if not isinstance(location, str):
            raise ValueError(f'Malformed async job location. Expected '
                             f'a string, got {type(logger)}: '
                             f'{str(location)}')

        if location.startswith('/'):
            location = location[1:]

        return location

    @staticmethod
    def _get_retry_after(headers: dict) -> int:
        """
        Get the number of seconds to wait before polling the service
        again. If no value is found, or it's mangled, we'll return 5
        seconds.

        :param headers: API response headers as a dict
        :return retry_after: An int defining the number of seconds to
        wait to make the next API call.
        """
        # docs are inconsistent about the header names
        retry_after = int_or_none(headers.get('Retry-After')) \
            or int_or_none(headers.get('retry_after')) or ASYNC_DEFAULT_RETRY_AFTER

        if not isinstance(retry_after, int):
            raise ValueError(f'Malformed async retry after value. '
                             f'Expected an int, got {type(retry_after)}:'
                             f' {str(retry_after)}')
        return retry_after

    @staticmethod
    def _get_status(headers: dict) -> str:
        """
        Get the job status (done, failed, processing, starting, maybe
        more) from the response headers and return it to the caller.

        :param headers: API response headers as a dict
        :return status: The status of the job as a string
        """
        # docs are inconsistent about the header names
        status = headers.get('Status') or headers.get('status')

        if not isinstance(status, str):
            raise ValueError(f'Malformed async status. Expected a string, '
                             f'got {type(status)}: {str(status)}')
        return status

    def _get_total_items(self, endpoint: str, limit: int = None) -> int:
        """
        This function queries the service to see how many items would be
        returned from a query. It is used to determine if we can use a
        simple GET or if we have to use their async get/wait/fetch.

        :return total_items: The number of devices that the query will return.
        """
        if limit and isinstance(limit, int):
            url_params = {'max_results': limit}
        else:
            url_params = None

        try:
            # test to see if we need to use async get/wait/fetch
            response = self._get(endpoint,
                                 return_response_raw=True,
                                 use_json_in_response=False,
                                 url_params=url_params,
                                 do_basic_auth=True
                                 )

            device_headers = response.headers
            if not isinstance(device_headers,
                              (dict, requests.structures.CaseInsensitiveDict)
                              ):
                logger.warning(f'Malformed response when fetching total items. '
                               f'Expected a dict-like object, got '
                               f'{type(device_headers)}: {str(device_headers)}')
                return ASYNC_DEVICE_TRIGGER

            # if we get a bad response, set to a number that will force async
            total_items = int_or_none(
                device_headers.get('X-Total-Count')) or ASYNC_DEVICE_TRIGGER

        except Exception as err:
            logger.exception(f'Unable to fetch total item count: {str(err)}')
            raise

        return total_items

    def _get_items_async(self, endpoint: str, device_type: str) -> list:
        all_items = list()
        try:
            # header is required to kick off async
            response = self._get(endpoint,
                                 return_response_raw=True,
                                 use_json_in_response=False,
                                 do_basic_auth=True,
                                 extra_headers=ASYNC_EXTRA_HEADERS
                                 )

            if not (isinstance(response, (dict, requests.models.Response)) and
                    response.status_code in SUCCESS_CODES):
                logger.warning(
                    f'Malformed response from {endpoint}. Expected a dict-like '
                    f'object, got {type(response)}: {str(response)} with '
                    f'status of {str(response.status_code)}')
            try:
                all_items = self._wait_for_job(response=response)
                if isinstance(all_items, list):
                    logger.debug(f'Found {len(all_items)} {device_type}')
                else:
                    message = f'Malformed response while waiting for job. ' \
                              f'Expected a list, got {type(all_items)}: ' \
                              f'{str(all_items)}'
                    logger.warning(message)
                    raise ValueError(message)
            except Exception as err:
                logger.exception(f'Unable to process asynchronous '
                                 f'{device_type} job: {str(err)}')
                raise

        except Exception as err:
            logger.exception(f'Unable to fetch {device_type} items '
                             f'asynchronously: {str(err)}')

        return all_items
