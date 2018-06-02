import logging
logger = logging.getLogger(f"axonius.{__name__}")

from typing import Iterable

import requests
import uritools


class OktaConnection:
    def __init__(self, url: str, api_key: str):
        self.__base_url = url
        self.__api_key = api_key

    def __make_request(self, api, params={}, forced_url=None):
        """
        Makes a request to the Okta service.
        Either 'api' or 'forced_url' must be provided.
        :param api: must be relative (i.e. 'api/v1/users')
        :param params: url GET parameters
        :param forced_url: must be absolute (i.e. 'https://axonius.okta.com/api/v1/users?after=2&limit=1')
        :return: response
        """
        assert bool(api) != bool(forced_url)
        headers = {
            'Authorization': f"SSWS {self.__api_key}"
        }
        return requests.get(forced_url or uritools.urijoin(self.__base_url, api), params=params, headers=headers)

    def is_alive(self):
        """
        Checks if the connection is valid
        :return: True if the connection is good, else returns the (erroneous) response
        """
        response = self.__make_request('api/v1/users', params={'limit': 1})
        if response.status_code == 200:
            return True
        return response

    def get_users(self) -> Iterable[dict]:
        """
        Fetches all users
        :return: iterable of dict
        """
        _MAX_PAGE_COUNT = 1000
        try:
            page_count = 0
            response = self.__make_request('api/v1/users')
            yield from response.json()
            while 'next' in response.links and page_count < _MAX_PAGE_COUNT:
                response = self.__make_request(forced_url=response.links['next']['url'])
                yield from response.json()
                page_count += 1
        except Exception:
            logger.exception("Exception while fetching users")
