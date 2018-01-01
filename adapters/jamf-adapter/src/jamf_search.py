import xml.etree.cElementTree as ET
import requests
from jamf_exceptions import JamfRequestException


class AdvancedSearchRAII(object):
    def __init__(self, jamf_connection, url, data):
        self.id = None
        self.jamf_connection = jamf_connection
        self.url = url
        self.data = data

    def __enter__(self):
        post_headers = self.jamf_connection.headers
        post_headers['Content-Type'] = 'application/xml'
        try:
            requests.delete(self.jamf_connection.get_url_request(self.url + "/name/Axonius-Inventory-123456"),
                            headers=self.jamf_connection.headers)
        except:
            pass
        response = requests.post(self.jamf_connection.get_url_request(self.url + "/id/0"),
                                 headers=post_headers,
                                 data=self.data)
        try:
            response.raise_for_status()
        except Exception as e:
            self.jamf_connection.logger.error(f"Search creation returned an error: {str(e)}")
            raise JamfRequestException(str(e))
        try:
            response_tree = ET.fromstring(response.text)
            self.id = int(response_tree.find("id").text)
        except ValueError:
            self.jamf_connection.logger.error(f"Search creation returned an error: {response.text}")
            raise JamfRequestException(f"Search creation returned an error: {response.text}")
        created = False
        tries = 0
        while not created and tries < 5:
            requests.get(self.jamf_connection.get_url_request(self.url + "/id/" + str(self.id)),
                         self.jamf_connection.headers)
            try:
                response.raise_for_status()
                created = True
            except requests.HTTPError as e:
                if "Not Found for url" in str(e):
                    tries += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.id is not None:
            requests.delete(self.jamf_connection.get_url_request(self.url + "/id/" + str(self.id)),
                            headers=self.jamf_connection.headers)
