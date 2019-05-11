import http.client
import logging
import math
import threading
from abc import ABC, abstractmethod
from json.decoder import JSONDecodeError
from typing import Tuple

import aiohttp
import requests
import uritools
from urllib3.util.url import parse_url

from axonius.async.utils import async_request
from axonius.clients.rest import consts
from axonius.clients.rest.exception import RESTException, RESTAlreadyConnected, \
    RESTConnectionError, RESTNotConnected, RESTRequestException
from axonius.utils.json import from_json

logger = logging.getLogger(f'axonius.{__name__}')


ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE = 50
MAX_REQUESTS_PER_MINUTE = 1000

# pylint: disable=R0902


class RESTConnection(ABC):
    # pylint: disable=R0913
    def __init__(self, domain: str, username: str = None, password: str = None, apikey: str = None,
                 verify_ssl: bool = False,
                 http_proxy: str = None, https_proxy: str = None, url_base_prefix: str = '/',
                 session_timeout: Tuple[int, int] = consts.DEFAULT_TIMEOUT,
                 port: int = None, headers: dict = None, use_domain_path: bool = False):
        """
        An abstract class that implements backbone logic for accessing RESTful APIs in the manner
        needed by adapters to facilitate device acquiring logic
        :param domain: The hostname of the api, e.g. 'https://facebook.com'
        :param username: if HTTP authentication is required, this will be the username
        :param password: if HTTP authentication is required, this will be the password
        :param apikey: TBD
        :param verify_ssl: passed to `requests` as is
        :param http_proxy: if present, this proxy will be used for HTTP
        :param https_proxy: if present, this proxy will be used for HTTPS
        :param url_base_prefix: base path for API, e.g. '/api/devices'
        :param session_timeout: passed to `requests` as is
        :param port: port to be used with the API
        :param headers: passed to `requests1 as is
        :param use_domain_path: If this is true we take the path from the url and not from url_base_prefix
        """
        self._domain = domain.strip()
        self._username = username
        self._password = password
        self._apikey = apikey
        self._verify_ssl = verify_ssl
        self._http_proxy = http_proxy
        self._https_proxy = https_proxy
        self._url_base_prefix = url_base_prefix
        if not self._url_base_prefix.startswith('/'):
            self._url_base_prefix = '/' + self._url_base_prefix
        if not self._url_base_prefix.endswith('/'):
            self._url_base_prefix = self._url_base_prefix + '/'
        self._session_timeout = session_timeout
        self._port = port
        self._proxies = {}
        if http_proxy is not None:
            self._proxies['http'] = http_proxy
        if https_proxy is not None:
            self._proxies['https'] = https_proxy
        logger.debug(f'Proxies: {self._proxies}')

        # We assumes that path starts with / and ends with /
        # Later in the code we will concat url to, and we will check that they don't start with /
        self._url = self.build_url(domain, port, self._url_base_prefix, use_domain_path)
        self._permanent_headers = headers if headers is not None else {}
        self._session_headers = {}
        self._session = None
        self._session_lock = threading.Lock()

    @staticmethod
    def build_url(domain: str, port: int = None, url_base_prefix: str = '/', use_domain_path: bool = False):
        """
        Parses the domain and composes the uri.
        :param domain: The hostname of the api, e.g. 'https://facebook.com'
        :param port: port to be used with the API
        :param url_base_prefix: base path for API, e.g. '/api/devices'
        :param use_domain_path: If this is true we take the path from the url and not from url_base_prefix
        """
        url_parsed = parse_url(domain)
        url_scheme = url_parsed.scheme or 'https'
        url_port = url_parsed.port or port
        if use_domain_path:
            path = url_parsed.path + '/'
        else:
            path = url_base_prefix
        return uritools.compose.uricompose(
            scheme=url_scheme, authority=url_parsed.host, port=url_port, path=path)

    def __del__(self):
        if hasattr(self, 'session') and self._is_connected:
            self.close()

    def connect(self):
        self._validate_no_connection()
        self._session = requests.Session()
        return self._connect()

    @staticmethod
    def test_reachability(host, port=None, path='/', ssl=True, use_domain_path=False):
        """
        Runs a basic http check to see if the host is reachable.
        :param host: The hostname of the api, e.g. 'https://facebook.com'
        :param port: port to be used with the API.
        :param path:
        :param ssl: Should be used with ssl.
        :param use_domain_path:
        :return:
        """
        try:
            parsed_url = RESTConnection.build_url(host, port if port else 443 if ssl else 80, url_base_prefix=path,
                                                  use_domain_path=use_domain_path)
            requests.get(parsed_url, verify=False, timeout=consts.DEFAULT_TIMEOUT)
            return True
        except requests.exceptions.ConnectionError as conn_err:
            # if 'Remote end closed connection without response' in conn_err:
            if isinstance(conn_err.args[0].args[-1], http.client.RemoteDisconnected):
                return True
            return False

    @abstractmethod
    def _connect(self):
        pass

    @abstractmethod
    def get_device_list(self):
        pass

    def _validate_no_connection(self):
        if self._is_connected:
            raise RESTAlreadyConnected('Already Connected')

    def close(self):
        """ Closes the connection """
        self._session.close()
        self._session = None
        self._session_headers = {}

    @property
    def _is_connected(self):
        return self._session is not None

    def _get_url_request(self, request_name):
        """ Builds and returns the full url for the request

        :param request_name: the request name
        :return: the full request url
        """
        if request_name.startswith('/'):
            raise RESTException(f'Url with double / : {self._url} AND {request_name}')
        return uritools.urijoin(self._url, request_name)

    def _get(self, *args, **kwargs):
        return self._do_request('GET', *args, **kwargs)

    @staticmethod
    def _is_async_response_good(response):
        return not isinstance(response, Exception)

    def _async_get(self, list_of_requests,
                   chunks=ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE,
                   max_requests_per_minute=MAX_REQUESTS_PER_MINUTE):
        return self._do_async_request('GET', list_of_requests, chunks, max_requests_per_minute)

    def _async_get_only_good_response(self, list_of_requests,
                                      chunks=ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE,
                                      max_requests_per_minute=MAX_REQUESTS_PER_MINUTE):

        for response in self._async_get(list_of_requests, chunks, max_requests_per_minute):
            if self._is_async_response_good(response):
                yield response
            else:
                logger.error(f'Async response returned bad, its {response}')

    def _post(self, *args, **kwargs):
        return self._do_request('POST', *args, **kwargs)

    def _async_post(self, list_of_requests,
                    chunks=ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE,
                    max_requests_per_minute=MAX_REQUESTS_PER_MINUTE):
        return self._do_async_request('POST', list_of_requests, chunks, max_requests_per_minute)

    def _delete(self, *args, **kwargs):
        return self._do_request('DELETE', *args, **kwargs)

    def _put(self, *args, **kwargs):
        return self._do_request('PUT', *args, **kwargs)

    def _patch(self, *args, **kwargs):
        return self._do_request('PATCH', *args, **kwargs)

    # pylint: disable=R0912, R0913, R0914
    def _do_request(self, method, name, url_params=None, body_params=None,
                    force_full_url=False, do_basic_auth=False, use_json_in_response=True, use_json_in_body=True,
                    do_digest_auth=False, return_response_raw=False, alternative_auth_dict=None, extra_headers=None,
                    raise_for_status=True):
        """ Serves a GET request to REST API

        :param str name: the name of the request
        :param dict url_params: GET additional parameters
        :param dict body_params: POST additional parameters
        :param bool force_full_url: Force using name as the full url name without prefix
        :param bool do_basic_auth: Use username and password as the basic auth parameters
        :param bool use_json_in_response: Use response.json() before returning results
        :param bool use_json_in_body: Whether or not to use json or data param in post function
        :param bool do_digest_auth: Use specific kind of auth called digest
        :param tuple alternative_auth_dict: Tuple for auth params if you don't want the regular username+pwd
        :param bool return_response_raw: Whether to return the response body as is or not
        :return: the response
        :rtype: dict
        """
        #
        #   Remember to change _do_async_request when adding/removing functionality here!
        #
        if not self._is_connected:
            raise RESTNotConnected()
        try:
            if force_full_url:
                url = name
            else:
                url = self._get_url_request(name)
            request_data = None
            request_json = None
            if use_json_in_body:
                request_json = body_params
            else:
                request_data = body_params
            auth_dict = None
            if do_basic_auth:
                if alternative_auth_dict:
                    auth_dict = alternative_auth_dict
                else:
                    if self._username is None or self._password is None:
                        raise RESTConnectionError('No user name or password')
                    auth_dict = (self._username, self._password)
            if do_digest_auth:
                auth_dict = requests.auth.HTTPDigestAuth(self._username, self._password)

            # If the same header exists in both headers, _session_headers win.
            headers_for_request = self._permanent_headers.copy()
            headers_for_request.update(self._session_headers)
            if extra_headers:
                headers_for_request.update(extra_headers)

            response = self._session.request(method, url, params=url_params,
                                             headers=headers_for_request, verify=self._verify_ssl,
                                             json=request_json, data=request_data,
                                             timeout=self._session_timeout, proxies=self._proxies,
                                             auth=auth_dict)
        except requests.HTTPError as e:
            self._handle_http_error(e)

        return self._handle_response(response,
                                     raise_for_status=raise_for_status,
                                     use_json_in_response=use_json_in_response,
                                     return_response_raw=return_response_raw)

    @staticmethod
    def _handle_http_error(error):
        try:
            # Try get the error if it comes back.
            try:
                rp = error.response.json()
            except Exception:
                rp = str(error.response.content)
            message = f'{str(error)}: {rp}'
        except Exception:
            message = str(error)
        raise RESTRequestException(message)

    def _handle_response(self, response, raise_for_status=True, use_json_in_response=True, return_response_raw=False):
        try:
            if raise_for_status:
                response.raise_for_status()
        except requests.HTTPError as e:
            self._handle_http_error(e)

        if use_json_in_response:
            try:
                return response.json()
            except JSONDecodeError as e:
                raise RESTRequestException(f'Got json error: {str(e)}')
        elif return_response_raw:
            return response
        else:
            return response.content

    # pylint: disable=R0915
    def _do_async_request(self, method, list_of_requests, chunks, max_requests_per_minute):
        """
        makes requests asynchronously. list_of_requests is a dict of parameters you would normally pass to _do_request.
        :param method:
        :param list_of_requests:
        :param chunks: the amount of chunks to send in parallel. If the total amount of requests is over, chunks will be
                       used. e.g., if chunks=100 and we have 150 requests, 100 will be parallel (asyncio) and then 50.
        :param max_requests_per_minute: the maximum of requests we can do per minute. if we pass it, time.sleep will
                                        wait a minute. unused
        :return:
        """
        #
        #   Remember to change _do_request when adding/removing functionality here!
        #
        if not self._is_connected:
            raise RESTNotConnected()

        # Transform regular to aio requests
        aio_requests = []

        for req in list_of_requests:
            aio_req = dict()
            aio_req['method'] = method

            # Build url
            if req.get('force_full_url', False) is True:
                aio_req['url'] = req['name']
            else:
                aio_req['url'] = self._get_url_request(req['name'])

            # Take care of url params
            url_params = req.get('url_params')
            if url_params is not None:
                aio_req['params'] = url_params

            # Take care of body params
            body_params = req.get('body_params')
            if body_params is not None:
                if req.get('use_json_in_body', True) is True:
                    aio_req['json'] = body_params
                else:
                    aio_req['data'] = body_params

            # Take care of auth
            if req.get('do_basic_auth', False) is True:
                aio_req['auth'] = (self._username, self._password)
            if req.get('do_digest_auth') is not None:
                raise ValueError(f'Async requests do not support digest auth')

            # Take care of headers, timeout and ssl verification
            aio_req['headers'] = self._permanent_headers.copy()
            aio_req['headers'].update(self._session_headers)
            aio_req['timeout'] = self._session_timeout
            if self._verify_ssl is False:
                aio_req['ssl'] = False

            # Take care of proxy. aiohttp doesn't allow us to try both proxies, we need to prefer one of them.
            if self._proxies.get('https'):
                aio_req['proxy'] = self._proxies['https']
            elif self._proxies.get('http'):
                aio_req['proxy'] = self._proxies['http']

            aio_requests.append(aio_req)

        # Now that we have built the new requests, try to asynchronously get them.
        for chunk_id in range(int(math.ceil(len(aio_requests) / chunks))):
            logger.debug(f'Async requests: sending {chunk_id * chunks} out of {len(aio_requests)}')
            all_answers = async_request(aio_requests[chunks * chunk_id: chunks * (chunk_id + 1)])

            # We got the requests, time to check if they are valid and transform them to what the user wanted.
            for i, raw_answer in enumerate(all_answers):
                request_id_absolute = chunks * chunk_id + i
                # The answer could be an exception
                if isinstance(raw_answer, Exception):
                    yield raw_answer

                # Or, it can be the actual response
                elif isinstance(raw_answer, tuple) and \
                        isinstance(raw_answer[0], str) and isinstance(raw_answer[1], aiohttp.ClientResponse):
                    try:
                        answer_text = raw_answer[0]
                        response_object = raw_answer[1]

                        response_object.raise_for_status()
                        if list_of_requests[request_id_absolute].get('return_response_raw', False) is True:
                            yield response_object
                        elif list_of_requests[request_id_absolute].get('use_json_in_response', True) is True:
                            yield from_json(answer_text)    # from_json also handles datetime with json.loads doesn't
                        else:
                            yield answer_text
                    except aiohttp.ClientResponseError as e:
                        try:
                            rp = from_json(answer_text)     # from_json also handles datetime with json.loads doesn't
                        except Exception:
                            rp = str(answer_text)
                        error_on = list_of_requests[request_id_absolute]['name']
                        yield RESTRequestException(f'async error code {e.status} on '
                                                   f'url {error_on} - {rp}')
                    except Exception as e:
                        logger.exception(f'Exception while parsing async response for text {answer_text}')
                        yield e
                else:
                    msg = f'Got an async response which is not exception or ClientResponse. ' \
                          f'This should never happen! response is {raw_answer}'
                    logger.error(msg)
                    yield ValueError(msg)

    def __enter__(self):
        if self._session_lock.acquire(blocking=False) is False:
            raise RESTAlreadyConnected('Already Connected')
        try:
            self.connect()
        except Exception:
            self.__exit()
            raise
        return self

    def __exit(self):
        try:
            self.close()
        finally:
            self._session_lock.release()

    # pylint: disable=C0103
    def __exit__(self, _type, value, tb):
        self.__exit()
