import xml.etree.cElementTree as ET
import requests
from jamf_exceptions import JamfRequestException


class JamfAdvancedSearch(object):
    def __init__(self, jamf_connection, url, data, headers, proxies):
        self.proxies = proxies
        self.jamf_connection = jamf_connection
        self.url = url
        self.search_results = None
        self.headers = headers
        self._update_query(data)

    def _request_for_query(self, request_method, url_addition, data, error_message):
        post_headers = self.jamf_connection.headers
        post_headers['Content-Type'] = 'application/xml'
        response = request_method(self.jamf_connection.get_url_request(self.url + url_addition),
                                  headers=post_headers,
                                  data=data,
                                  proxies=self.proxies)
        try:
            response.raise_for_status()
            response_tree = ET.fromstring(response.text)
            int(response_tree.find("id").text)
        except ValueError:
            # conversion of the query id to int failed
            self.jamf_connection.logger.exception(error_message + f": {response.text}")
            raise JamfRequestException(error_message + f": {response.text}")
        except Exception as e:
            # any other error during creation of the query or during the conversion
            self.jamf_connection.logger.exception(error_message)
            raise JamfRequestException(error_message + str(e))

    def _update_query(self, data):
        try:
            self._request_for_query(requests.delete, "/name/Axonius-Adapter-Inventory", data,
                                    "Search update returned an error")
            self._request_for_query(requests.put, "/name/Axonius-Adapter-Inventory", data,
                                    "Search update returned an error")
        except JamfRequestException:
            self._request_for_query(requests.post, "/id/0", data, "Search creation returned an error")

    def _get_query_results(self):
        try:
            response = requests.get(self.jamf_connection.get_url_request(self.url + "/name/Axonius-Adapter-Inventory"),
                                    headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            self.jamf_connection.logger.warn(f"Our search query doesn't exist: {str(e)}")
            return None
        except Exception as e:
            self.jamf_connection.logger.warn(f"An unknown error has occurred: {str(e)}")
            raise JamfRequestException(f"An unknown error has occurred: {str(e)}")

    def __enter__(self):
        tries = 0
        while self.search_results is None:
            self.search_results = self._get_query_results()
            tries += 1
            if tries >= 5:
                self.jamf_connection.logger.error(f"Search creation succeeded but no results returned after 5 times")
                raise JamfRequestException(f"Search creation succeeded but no results returned after 5 times")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.search_results = None
