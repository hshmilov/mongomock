import os
import time

import requests

from ui_tests.tests.ui_test_base import TestBase


def _get_peer_ssl(address, verify):
    # pylint: disable=W0212
    # pylint: disable=C0103
    # pylint: disable=no-member
    # Getting the peer ssl cert isn't trivial
    # https://stackoverflow.com/questions/16903528/how-to-get-response-ssl-certificate-from-requests-in-python
    HTTPResponse = requests.packages.urllib3.response.HTTPResponse
    orig_HTTPResponse__init__ = HTTPResponse.__init__
    HTTPAdapter = requests.adapters.HTTPAdapter
    orig_HTTPAdapter_build_response = HTTPAdapter.build_response
    # pylint: enable=no-member

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
        self.settings_page.wait_for_toaster(
            'Hostname does not match the hostname in the certificate file, hostname in given cert is localhost')

        # Test that the right hostname works
        self.settings_page.set_global_ssl_settings('localhost', cert_data, private_data)
        self.settings_page.click_save_button()

        try:
            self.settings_page.wait_for_saved_successfully_toaster()

            self.settings_page.refresh()
            try:
                time.sleep(10)
                peercert = _get_peer_ssl('https://localhost', crt_filename)
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
            self.settings_page.wait_for_saved_successfully_toaster()

    @staticmethod
    def read_ca_cert_file(ca_filename: str):
        certs_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                       '../../ssl_keys_for_tests'))

        ca_filename = os.path.join(certs_base_path, ca_filename)
        cert_data = open(ca_filename, 'rb').read()
        return cert_data

    def test_add_ca_certificate(self):

        def add_new_ca_file():
            cert_info = self.settings_page.get_first_ca_cert_fields_info()
            self.settings_page.assert_ca_file_before_upload(cert_info)
            self.settings_page.assert_ca_cert_first_file_input_type()
            # upload and save
            apple_root_ca_cert = self.read_ca_cert_file('apple_root_ca.cer')
            self.settings_page.upload_ca_cert_file(apple_root_ca_cert)
            self.settings_page.save_and_wait_for_toaster()

        def add_addtional_ca_cert():
            # press + for addtional ca row
            self.settings_page.click_add_ca_cert()
            # upload and save
            versign_root_ca_cert = self.read_ca_cert_file('verigsin_class1.cer')
            self.settings_page.upload_ca_cert_file(versign_root_ca_cert, ca_file_index=2)
            # submit
            self.settings_page.save_and_wait_for_toaster()
            self.settings_page.wait_for_toaster_to_end(self.settings_page.SAVED_SUCCESSFULLY_TOASTER)

        def verify_ca_certs_list():
            self.settings_page.switch_to_page()
            self.settings_page.refresh()
            self.settings_page.click_global_settings()
            # cert file list got updated with both new ca files
            cert_info = self.settings_page.get_first_ca_cert_fields_info()
            self.settings_page.assert_ca_file_name_after_upload(cert_info)
            cert_info = self.settings_page.get_second_ca_cert_fields_info()
            self.settings_page.assert_ca_file_name_after_upload(cert_info)

        def delete_ca_files():
            self.settings_page.ca_cert_delete_second()
            self.settings_page.ca_cert_delete_first()
            self.settings_page.save_and_wait_for_toaster()

        def verify_ca_files_deleted():
            self.settings_page.refresh()
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            assert self.settings_page.is_cert_file_item_deleted()
            assert self.settings_page.is_cert_file_item_deleted(ca_delete_index=2)

        try:
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            # enable custom ca
            self.settings_page.enable_custom_ca()
            self.settings_page.click_add_ca_cert()
            add_new_ca_file()
            add_addtional_ca_cert()
            verify_ca_certs_list()
            delete_ca_files()
            verify_ca_files_deleted()

        finally:
            self.settings_page.refresh()
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            self.settings_page.disable_custom_ca()
            if not self.settings_page.is_cert_file_item_deleted():
                self.settings_page.ca_cert_delete_first()
            if not self.settings_page.is_cert_file_item_deleted(ca_delete_index=2):
                self.settings_page.ca_cert_delete_second()
            self.settings_page.save_and_wait_for_toaster()
