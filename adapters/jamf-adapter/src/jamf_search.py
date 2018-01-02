import xml.etree.cElementTree as ET
import requests
from jamf_exceptions import JamfRequestException


class AdvancedSearchRAII(object):
    def __init__(self, jamf_connection, url, data):
        self.jamf_connection = jamf_connection
        self.url = url
        self.data = data
        self.search_results = None

    def _create_query(self):
        post_headers = self.jamf_connection.headers
        post_headers['Content-Type'] = 'application/xml'
        response = requests.post(self.jamf_connection.get_url_request(self.url + "/id/0"),
                                 headers=post_headers,
                                 data=self.data)
        try:
            response.raise_for_status()
            response_tree = ET.fromstring(response.text)
            int(response_tree.find("id").text)
        except ValueError:
            # conversion of the query id to int failed
            self.jamf_connection.logger.error(f"Search creation returned an error: {response.text}")
            raise JamfRequestException(f"Search creation returned an error: {response.text}")
        except Exception as e:
            # any other error during creation of the query or during the conversion
            self.jamf_connection.logger.error(f"Search creation returned an error: {str(e)}")
            raise JamfRequestException(str(e))

    def _get_query_results(self):
        try:
            response = requests.get(self.jamf_connection.get_url_request(self.url + "/name/Axonius-Adapter-Inventory"),
                                    headers=self.jamf_connection.headers)
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            self.jamf_connection.logger.warn(f"Our search query doesn't exist: {str(e)}")
            return None
        except Exception as e:
            self.jamf_connection.logger.warn(f"An unknown error has occurred: {str(e)}")
            raise JamfRequestException(f"An unknown error has occurred: {str(e)}")

    def __enter__(self):
        self.search_results = self._get_query_results()
        if self.search_results is None:
            self._create_query()

        tries = 0
        while self.search_results is None:
            self.search_results = self._get_query_results()
            tries += 1
            if tries >= 5:
                self.jamf_connection.logger.error(f"Search creation succeeded but no results returned after 5 times")
                raise JamfRequestException(f"Search creation succeeded but no results returned after 5 times")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.search_results = None
