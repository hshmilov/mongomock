import requests
from jamf_adapter.exceptions import JamfRequestException
from jamf_adapter.consts import ADVANCE_SEARCH_NAME


class JamfAdvancedSearch(object):
    def __init__(self, jamf_connection, url, data):
        self.jamf_connection = jamf_connection
        self.url = url
        self.search_results = None
        self._update_query(data)

    def _update_query(self, data):
        try:
            self.jamf_connection.jamf_request(requests.delete, self.url + ADVANCE_SEARCH_NAME, data,
                                              "Search update returned an error")
        finally:
            self.jamf_connection.jamf_request(requests.post, self.url + "/id/0", data,
                                              "Search creation returned an error")

    def __enter__(self):
        tries = 0
        while self.search_results is None:
            try:
                self.search_results = self.jamf_connection.get(self.url + ADVANCE_SEARCH_NAME)
            except Exception:
                tries += 1
                if tries >= 5:
                    self.jamf_connection.logger.error(
                        f"Search creation succeeded but no results returned after 5 times")
                    raise JamfRequestException(f"Search creation succeeded but no results returned after 5 times")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.search_results = None
