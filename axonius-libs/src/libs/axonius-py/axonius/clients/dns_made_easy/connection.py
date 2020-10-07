import hmac
import logging

from hashlib import sha1
from time import strftime, gmtime, sleep
from typing import Iterable

import requests

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

from axonius.clients.dns_made_easy.consts import API_VERSION, STRFTIME_DATE_GMT, \
    ALL_DOMAINS_ENDPOINT, REQUEST_LIMIT, SLEEP_TIME, REMAINING_REQUESTS_HEADER
from axonius.utils.parsing import int_or_none

logger = logging.getLogger(f'axonius.{__name__}')


class DnsMadeEasyConnection(RESTConnection):
    """ rest client for DnsMadeEasy adapter """

    def __init__(self, secret_key: str, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix=API_VERSION,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self.__secret_key = secret_key

    def _set_authentication_headers(self):
        current_time_gmt = self._get_time()

        self._session_headers['x-dnsme-apiKey'] = self._apikey
        self._session_headers['x-dnsme-requestDate'] = current_time_gmt
        self._session_headers['x-dnsme-hmac'] = self._get_hmac(
            init_vector=self.__secret_key.encode('utf-8'),
            value=current_time_gmt.encode('utf-8')
        )

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')

        if not self.__secret_key:
            raise RESTException('No Secret Key')

        try:
            self._set_authentication_headers()

            # connect_url = f'https://{self._domain}/{API_VERSION}/{ALL_DOMAINS_ENDPOINT}'
            response = self._get(ALL_DOMAINS_ENDPOINT)
            if not (isinstance(response, dict) and response.get('data')):
                raise ValueError(f'No data was returned.')

        except Exception as err:
            raise ValueError(f'Error: Invalid response from server, please '
                             f'check domain or credentials. {str(err)}')

    def get_device_list(self):
        try:
            yield from self._get_all_domains()
        except RESTException as err:
            logger.exception(f'{str(err)}')
            raise

    # pylint: disable=invalid-triple-quote, too-many-statements
    # pylint: disable=too-many-nested-blocks, too-many-branches
    def _get_all_domains(self) -> Iterable[dict]:
        """
        Query DNSME to get basic information on all domains that are
        using the service in the user's account. Extract the domain ID
        and use it to pull deeper domain data and the domain records,
        which will become the device (subdomain as device). All of this
        data is yielded to the caller to create a device.

        NOTE: Only 150 queries are allowed per 5 min across the entire
        API, so be careful

        NOTE: There is no documentation around pagination, but the sample
        data hints that it exists ('totalPages' and 'page'). This is
        likely to be an issue in the field, but will fail only if the
        number of domains is greater than 499.


        device name value (www)
        hostname should be www.example.com
        NOT 1.1.1.1@example.com
        """
        try:
            # the authentication headers are very short-lived. regen them for each call
            self._set_authentication_headers()

            # pull basic domain data
            # all_domains_url = f'http://{self._domain}/{API_VERSION}/{ALL_DOMAINS_ENDPOINT}/'
            response = self._get(ALL_DOMAINS_ENDPOINT)
            if not isinstance(response, dict):
                message = f'Malformed response while fetching all ' \
                          f'domains. Expected a dict, got ' \
                          f'{type(response)}: {str(response)}'
                logger.warning(message)
                raise ValueError(message)

            domains = response.get('data')
            if not isinstance(domains, list):
                raise ValueError(f'Malformed domains data. Expected a list, '
                                 f'got {type(domains)}: {str(domains)}')

            for domain in domains:
                if not isinstance(domain, dict):
                    logger.warning(f'Malformed domain. Expected a dict, got a '
                                   f'{type(domain)}: {str(domain)}')
                    continue

                domain_id = domain.get('id')
                if not isinstance(domain_id, int):
                    logger.warning(f'Malformed domain ID. Expected an int, got '
                                   f'{type(domain_id)}: {str(domain_id)}')
                    continue

                # populate a few fields for easy access
                domain_data = dict()
                domain_data['id'] = domain_id
                domain_data['name'] = domain.get('name')
                domain_data['basic_domain_data'] = domain

                # enrich the basic data captured above
                try:
                    enriched_data = self._get_enriched_domain_info(domain_id=domain_id)
                    if isinstance(enriched_data, dict):
                        domain_data['enriched'] = enriched_data
                    else:
                        logger.warning(f'Malformed enriched data. Expected a '
                                       f'dict, got {type(enriched_data)}: '
                                       f'{str(enriched_data)}')
                        # fallthrough: this data is nice to have but not a show-stopper

                except Exception as err:
                    logger.exception(f'Unable to fetch domain enrichment '
                                     f'data: {str(err)}')
                    # fallthrough: not required data

                # get domain record data
                try:
                    record_data = self._get_single_domain_records(domain_id=domain_id)
                    if isinstance(record_data, list):
                        domain_data['records'] = record_data
                    else:
                        message = f'Malformed domain record data. Expected a ' \
                                  f'list, got {type(record_data)}: ' \
                                  f'{str(record_data)}'
                        logger.warning(message)
                        raise ValueError(message)

                except Exception:
                    logger.exception(f'Unable to fetch domain records for {domain_id}')
                    raise

                yield domain_data

        except Exception as err:
            logger.exception(f'Unable to fetch domains: {str(err)}')
            raise

    def _get_enriched_domain_info(self, domain_id: int) -> dict:
        """
        Fetch additional information on the domain using the domain ID
        and return it as a dictionary.

        NOTE:
        There may be issues here since the docs show that the response
        differs from what we've seen in the other API calls. This call
        appears to lack the pagination hints and 'data' element, so the
        flow looks a little different too.

        :param domain_id: The DNSME ID for the domain itself
        :return domain_info: A dictionary of enriched domain data
        """
        try:
            # the authentication headers are very short-lived. regen them for each call
            self._set_authentication_headers()

            # enriched_data_url = f'https://{self._domain}/{API_VERSION}/{ALL_DOMAINS_ENDPOINT}/{domain_id}'
            response = self._get(f'{ALL_DOMAINS_ENDPOINT}/{domain_id}')
            if not isinstance(response, dict):
                message = f'Malformed response while fetching domain info ' \
                          f'for {domain_id}. Expected a dict, got ' \
                          f'{type(response)}: {str(response)}'
                logger.warning(message)
                raise ValueError(message)

            # compensation for an atypical response
            domain_info = response.get('data') or response
            if not isinstance(domain_info, dict):
                logger.warning(f'Malformed enriched domain info. Expected a '
                               f'dict, got {type(domain_info)}: {str(domain_info)}')
                raise ValueError

            return domain_info
        except Exception as err:
            logger.exception(f'Unable to fetch enriched domain data: {str(err)}')
            raise

    def _get_single_domain_records(self, domain_id: int) -> list:
        """
        Take the passed domain_id and query the DNSME service to pull back
        domain records for a specific domain.

        NOTE: Only 150 queries are allowed per 5 min, so be careful

        :param domain_id: An integer representing a domain record
        :returns: A list of data about the given domain_id
        """
        try:
            # the authentication headers are very short-lived. regen them for each call
            self._set_authentication_headers()

            # single_domain_url = f'https://{self._domain}/{API_VERSION}/{ALL_DOMAINS_ENDPOINT}/{domain_id}/records'
            response = self._get(f'{ALL_DOMAINS_ENDPOINT}/{domain_id}/records')
            if not isinstance(response, dict):
                message = f'Malformed response while fetching domain records ' \
                          f'for {domain_id}. Expected a dict, got ' \
                          f'{type(response)}: {str(response)}'
                logger.warning(message)
                raise ValueError(message)

            domain_records = response.get('data')
            if not isinstance(domain_records, list):
                message = f'Malformed domain records. Expected a list, got ' \
                          f'{type(domain_records)}: {str(domain_records)}'
                logger.warning(message)
                raise ValueError(message)

            return domain_records

        except Exception as err:
            logger.exception(f'Unable to fetch domain records for {domain_id}: '
                             f'{str(err)}')
            raise

    @staticmethod
    def _get_time() -> str:
        return strftime(STRFTIME_DATE_GMT, gmtime())

    @staticmethod
    def _get_hmac(init_vector: bytes, value: bytes) -> str:
        return hmac.new(init_vector, value, sha1).hexdigest()

    def remove_subdomain_from_dns_made_easy(self, device: dict):
        """
        This function is used by the EC in order to delete records from a
        domain according to the results of a saved query.

        :param device: A dictionary that contains the domain ID and record ID
        for each device that matches the saved query
        """
        domain_id = device.get('domain_id')
        record_id = device.get('record_id')

        try:
            # the authentication headers are very short-lived. regen them for each call
            self._set_authentication_headers()

            # no response is kept here, since it is always an empty byte-string
            response = self._delete(f'{ALL_DOMAINS_ENDPOINT}/{domain_id}/records/{record_id}',
                                    return_response_raw=True,
                                    use_json_in_response=False
                                    )
            return True, 'Success'
        except Exception as err:
            message = f'Unable to delete record {record_id} from ' \
                      f'domain {domain_id}: {str(err)}'
            logger.exception(message)
            return False, message

    # pylint: disable=arguments-differ
    def _handle_response(self, response, *args, **kwargs):
        """
        Override the RESTConnection _handle_response in order to implement a
        retry mechanism. This API does not respond with a normal HTTP 429
        response, but with a response header that tells you how many API
        requests you have remaining to use in a _rolling 5-minute_ window.

        :param response: A Python request response object
        :return response: The response object is passed back to the
        overridden _handle_response()
        """
        headers = response.headers
        if not (headers and isinstance(headers, (dict, requests.structures.CaseInsensitiveDict))):
            message = f'Malformed response headers. Expected a dict, got ' \
                      f'{type(headers)}: {str(headers)}'
            logger.warning(message)
            raise ValueError(message)

        # this is the rate limit, showing how many API calls can be made before
        #   exceeding the threshold
        remaining_requests = int_or_none(headers.get(REMAINING_REQUESTS_HEADER))

        if remaining_requests is None:
            message = f'Remaining requests returned NoneType'
            logger.warning(message)
            raise ValueError(message)

        logger.debug(f'Requests remaining: {remaining_requests}')
        if remaining_requests <= REQUEST_LIMIT:
            logger.info(f'Waiting {SLEEP_TIME} seconds due to rate limiting')
            sleep(SLEEP_TIME)

        return super()._handle_response(response, *args, **kwargs)
