import logging
from typing import Tuple

logger = logging.getLogger(f"axonius.{__name__}")
from urllib3.util.url import parse_url
import uritools
import requests
from axonius.clients.rest import consts
from axonius.clients.rest.exception import *
from abc import ABC, abstractmethod
from json.decoder import JSONDecodeError


class RESTConnection(ABC):
    def __init__(self, domain: str, username: str = None, password: str = None, apikey: str = None,
                 verify_ssl: bool = False,
                 http_proxy: str = None, https_proxy: str = None, url_base_prefix: str = "/",
                 session_timeout: Tuple[int, int] = consts.DEFAULT_TIMEOUT,
                 port: int = None, headers: dict = {}):
        """
        An abstract class that implements backbone logic for accessing RESTful APIs in the manner
        needed by adapters to facilitate device acquiring logic
        :param domain: The hostname of the api, e.g. "https://facebook.com"
        :param username: if HTTP authentication is required, this will be the username
        :param password: if HTTP authentication is required, this will be the password
        :param apikey: TBD
        :param verify_ssl: passed to `requests` as is
        :param http_proxy: if present, this proxy will be used for HTTP
        :param https_proxy: if present, this proxy will be used for HTTPS
        :param url_base_prefix: base path for API, e.g. "/api/devices"
        :param session_timeout: passed to `requests` as is
        :param port: port to be used with the API
        :param headers: passed to `requests1 as is
        """
        self._domain = domain
        self._username = username
        self._password = password
        self._apikey = apikey
        self._verify_ssl = verify_ssl
        self._http_proxy = http_proxy
        self._https_proxy = https_proxy
        self._url_base_prefix = url_base_prefix
        if not self._url_base_prefix.startswith("/"):
            self._url_base_prefix = "/" + self._url_base_prefix
        if not self._url_base_prefix.endswith("/"):
            self._url_base_prefix = self._url_base_prefix + "/"
        self._session_timeout = session_timeout
        self._port = port
        self._proxies = {}
        if http_proxy is not None:
            self._proxies['http'] = http_proxy
        if https_proxy is not None:
            self._proxies['https'] = https_proxy
        logger.debug(f"Proxies: {self._proxies}")
        url_parsed = parse_url(domain)
        url_scheme = url_parsed.scheme or "https"
        url_port = url_parsed.port or self._port
        self._url = uritools.compose.uricompose(
            scheme=url_scheme, authority=url_parsed.host, port=url_port, path=self._url_base_prefix)
        self._permanent_headers = headers
        self._session_headers = {}
        self._session = None

    def __del__(self):
        if hasattr(self, 'session') and self._is_connected:
            self.close()

    def connect(self):
        self._validate_no_connection()
        self._session = requests.Session()
        return self._connect()

    @abstractmethod
    def _connect(self):
        pass

    @abstractmethod
    def get_device_list(self):
        pass

    def _validate_no_connection(self):
        if self._is_connected:
            raise RESTAlreadyConnected("Already Connected")

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
        if request_name.startswith("/"):
            raise RESTException(f"Url with double / : {self._url} AND {request_name}")
        return uritools.urijoin(self._url, request_name)

    def _get(self, *args, **kwargs):
        return self._do_request("GET", *args, **kwargs)

    def _post(self, *args, **kwargs):
        return self._do_request("POST", *args, **kwargs)

    def _delete(self, *args, **kwargs):
        return self._do_request("DELETE", *args, **kwargs)

    def _put(self, *args, **kwargs):
        return self._do_request("PUT", *args, **kwargs)

    def _do_request(self, method, name, url_params={}, body_params=None,
                    force_full_url=False, do_basic_auth=False, use_json_in_response=True, use_json_in_body=True,
                    do_digest_auth=False, return_response_raw=False):
        """ Serves a GET request to REST API

        :param str name: the name of the request
        :param dict url_params: GET additional parameters
        :param dict body_params: POST additional parameters
        :param bool force_full_url: Force using name as the full url name without prefix
        :param bool do_basic_auth: Use username and password as the basic auth parameters
        :param bool use_json_in_response: Use response.json() before returning results
        :param bool use_json_in_body: Whether or not to use json or data param in post function
        :param bool do_digest_auth: Use specific kind of auth called digest
        :param bool return_response_raw: Whether to return the response body as is or not
        :return: the response
        :rtype: dict
        """
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
                if self._username is None or self._password is None:
                    raise RESTConnectionError("No user name or password")
                auth_dict = (self._username, self._password)
            if do_digest_auth:
                auth_dict = requests.auth.HTTPDigestAuth(self._username, self._password)

            # If the same header exists in both headers, _session_headers win.
            headers_for_request = self._permanent_headers.copy()
            headers_for_request.update(self._session_headers)
            response = self._session.request(method, url, params=url_params,
                                             headers=headers_for_request, verify=self._verify_ssl,
                                             json=request_json, data=request_data,
                                             timeout=self._session_timeout, proxies=self._proxies,
                                             auth=auth_dict)
            response.raise_for_status()
        except requests.HTTPError as e:
            try:
                # Try get the error if it comes back.
                try:
                    rp = response.json()
                except Exception:
                    rp = str(response.content)
                message = f"{str(e)}: {rp}"
            except Exception:
                message = str(e)
            raise RESTRequestException(message)
        if use_json_in_response:
            try:
                return response.json()
            except JSONDecodeError as e:
                raise RESTRequestException(f"Got json error: {str(e)}")
        elif return_response_raw:
            return response
        else:
            return response.content

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
