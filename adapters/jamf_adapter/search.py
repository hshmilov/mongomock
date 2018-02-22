import requests
from jamf_adapter.exceptions import JamfRequestException
from jamf_adapter.consts import ADVANCE_SEARCH_URL_NAME


class JamfAdvancedSearch(object):
    def __init__(self, jamf_connection, url, data, search_name, all_permissions):
        """
        A class to handle a jamf search
        :param jamf_connection: the connection to the jamf cloud server
        :param url: the url of the search - advancedcomputersearch or mobiledevicesearch
        :param data: the search query
        :param search_name: the search name
        :param all_permissions: whether we have sufficient permissions to create and delete searches
        """
        self.jamf_connection = jamf_connection
        self.url = url
        self.search_results = None
        self.search_name = ADVANCE_SEARCH_URL_NAME.format(search_name)
        if all_permissions:
            self._update_query(data)

    def _update_query(self, data):
        try:
            self.jamf_connection.jamf_request(requests.delete, self.url + self.search_name, data,
                                              "Search update returned an error")
        finally:
            self.jamf_connection.jamf_request(requests.post, self.url + "/id/0", data,
                                              "Search creation returned an error")

    def __enter__(self):
        tries = 0
        while self.search_results is None:
            try:
                self.search_results = self.jamf_connection.get(self.url + self.search_name)
            except Exception:
                tries += 1
                if tries >= 5:
                    self.jamf_connection.logger.error(
                        f"Search creation succeeded but no results returned after 5 times")
                    raise JamfRequestException(f"Search creation succeeded but no results returned after 5 times")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.search_results = None
