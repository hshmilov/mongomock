import os
import time

import requests

from ui_tests.tests.ui_test_base import TestBase


def _get_peer_ssl(address, verify):
    # pylint: disable=W0212
    # pylint: disable=C0103
    # Getting the peer ssl cert isn't trivial
    # https://stackoverflow.com/questions/16903528/how-to-get-response-ssl-certificate-from-requests-in-python
    HTTPResponse = requests.packages.urllib3.response.HTTPResponse
    orig_HTTPResponse__init__ = HTTPResponse.__init__
    HTTPAdapter = requests.adapters.HTTPAdapter
    orig_HTTPAdapter_build_response = HTTPAdapter.build_response

    try:
        def new_HTTPResponse__init__(self, *args, **kwargs):
            orig_HTTPResponse__init__(self, *args, **kwargs)
            try:
                self.peercert = self._connection.sock.getpeercert()
            except AttributeError:
                pass

        HTTPResponse.__init__ = new_HTTPResponse__init__

        def new_HTTPAdapter_build_response(self, request, resp):
            response = orig_HTTPAdapter_build_response(self, request, resp)
            try:
                response.peercert = resp.peercert
            except AttributeError:
                pass
            return response

        HTTPAdapter.build_response = new_HTTPAdapter_build_response

        return requests.get(address,
                            verify=verify).peercert
    finally:
        HTTPAdapter.build_response = orig_HTTPAdapter_build_response
        HTTPResponse.__init__ = orig_HTTPResponse__init__


class TestGlobalSSL(TestBase):
    def test_global_ssl(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.open_global_ssl_toggle()
        keys_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                      '../../ssl_keys_for_tests'))

        crt_filename = os.path.join(keys_base_path, 'localhost.crt')
        cert_data = open(crt_filename, 'r').read()
        private_data = open(os.path.join(keys_base_path, 'localhost.key'), 'r').read()

        # Test that wrong hostname produces an error
        self.settings_page.set_global_ssl_settings('badhostname', cert_data, private_data)
        self.settings_page.click_save_button()
        self.settings_page.find_toaster(
            'Hostname does not match the hostname in the certificate file, hostname in given cert is localhost')

        # Test that the right hostname works
        self.settings_page.set_global_ssl_settings('localhost', cert_data, private_data)
        self.settings_page.click_save_button()

        try:
            self.settings_page.find_saved_successfully_toaster()

            self.settings_page.refresh()
            try:
                time.sleep(10)
                peercert = _get_peer_ssl(self.base_url, crt_filename)
                # In this path, we check that the certificate is good
                peercert_parsed = dict(i[0] for i in peercert['subject'])
                assert peercert_parsed['commonName'] == 'localhost'
            except requests.exceptions.SSLError as e:
                # In this path, it means that the URL of the GUI isn't localhost, which is GOOD, because it
                # means it failed verification and the SSL lib will report it back
                assert 'doesn\'t match \'localhost\'' in str(e)
        finally:
            # restore the previous setting: no SSL override
            self.settings_page.click_global_settings()
            self.settings_page.open_global_ssl_toggle(make_yes=False)
            self.settings_page.click_save_button()
            self.settings_page.find_saved_successfully_toaster()
