import json
import os
import re
import time

import pytest
import requests
from selenium.common.exceptions import NoSuchElementException

from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.tests.ui_test_base import TestBase

CERT_SUCCESS_TOASTER_MSG = 'Certificate settings saved successfully'


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
        self.settings_page.click_certificate_settings()
        keys_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                      '../../ssl_keys_for_tests'))

        crt_filename = os.path.join(keys_base_path, 'localhost.crt')
        cert_data = open(crt_filename, 'r').read()
        private_data = open(os.path.join(keys_base_path, 'localhost.key'), 'r').read()

        # Test that wrong hostname produces an error
        self.settings_page.set_global_ssl_settings('badhostname', cert_data, private_data)
        self.settings_page.click_modal_approve()
        self.settings_page.wait_for_toaster(
            'Hostname does not match the hostname in the certificate file, hostname in given cert is localhost')

        # Test that the right hostname works
        self.settings_page.set_global_ssl_settings('localhost', cert_data, private_data)
        self.settings_page.click_modal_approve()

        try:
            self.settings_page.wait_for_saved_successfully_toaster(toaster_message='Certificate imported successfully')

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
            self.settings_page.click_certificate_settings()
            self.settings_page.click_reset_to_defaults()
            self.settings_page.wait_for_saved_successfully_toaster(
                toaster_message='Certificate settings resetted successfully')

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
            self.settings_page.save_and_wait_for_toaster(toaster_message=CERT_SUCCESS_TOASTER_MSG)

        def add_addtional_ca_cert():
            # press + for addtional ca row
            self.settings_page.click_add_ca_cert()
            # upload and save
            versign_root_ca_cert = self.read_ca_cert_file('verigsin_class1.cer')
            self.settings_page.upload_ca_cert_file(versign_root_ca_cert, ca_file_index=2)
            # submit
            self.settings_page.save_and_wait_for_toaster(toaster_message=CERT_SUCCESS_TOASTER_MSG)
            self.settings_page.wait_for_toaster_to_end(CERT_SUCCESS_TOASTER_MSG)

        def verify_ca_certs_list():
            self.settings_page.switch_to_page()
            self.settings_page.refresh()
            self.settings_page.click_certificate_settings()
            # cert file list got updated with both new ca files
            cert_info = self.settings_page.get_first_ca_cert_fields_info()
            self.settings_page.assert_ca_file_name_after_upload(cert_info)
            cert_info = self.settings_page.get_second_ca_cert_fields_info()
            self.settings_page.assert_ca_file_name_after_upload(cert_info)

        def delete_ca_files():
            self.settings_page.ca_cert_delete_second()
            self.settings_page.ca_cert_delete_first()
            self.settings_page.save_and_wait_for_toaster(toaster_message=CERT_SUCCESS_TOASTER_MSG)

        def verify_ca_files_deleted():
            self.settings_page.refresh()
            self.settings_page.switch_to_page()
            self.settings_page.click_certificate_settings()
            assert self.settings_page.is_cert_file_item_deleted()
            assert self.settings_page.is_cert_file_item_deleted(ca_delete_index=2)

        try:
            self.settings_page.switch_to_page()
            self.settings_page.click_certificate_settings()
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
            self.settings_page.click_certificate_settings()
            self.settings_page.disable_custom_ca()
            if not self.settings_page.is_cert_file_item_deleted():
                self.settings_page.ca_cert_delete_first()
            if not self.settings_page.is_cert_file_item_deleted(ca_delete_index=2):
                self.settings_page.ca_cert_delete_second()
            self.settings_page.save_and_wait_for_toaster(toaster_message=CERT_SUCCESS_TOASTER_MSG)

    def _fill_csr_request(self, initial=False, bad_country=False):
        if initial:
            assert not self.settings_page.get_modal_approve_button_status()
        self.settings_page.fill_text_field_by_element_id('hostname', 'shukka.com')
        if initial:
            assert self.settings_page.get_modal_approve_button_status()
        self.settings_page.fill_text_field_by_element_id('alt_names', 'shukki.net')
        self.settings_page.fill_text_field_by_element_id('organization', 'organi')
        self.settings_page.fill_text_field_by_element_id('OU', 'OUOU')
        self.settings_page.fill_text_field_by_element_id('location', 'North Japan')
        self.settings_page.fill_text_field_by_element_id('state', 'JAJA')
        if bad_country:
            self.settings_page.fill_text_field_by_element_id('country', 'JPa')
        else:
            self.settings_page.fill_text_field_by_element_id('country', 'JP')
        self.settings_page.fill_text_field_by_element_id('email', 'aaaaaaaaa')
        if initial:
            assert not self.settings_page.get_modal_approve_button_status()
        self.settings_page.fill_text_field_by_element_id('email', 'a@a.com')
        if initial:
            assert self.settings_page.get_modal_approve_button_status()

    @staticmethod
    def _get_csr_file():
        resp = requests.post('https://127.0.0.1/api/login',
                             data=json.dumps({
                                 'user_name': DEFAULT_USER['user_name'],
                                 'password': DEFAULT_USER['password'],
                                 'remember_me': False
                             }),
                             verify=False)
        session = re.findall('session=(.*?);', resp.headers['Set-Cookie'])[0]
        resp.close()
        resp = requests.get('https://127.0.0.1/api/certificate/csr',
                            headers={'Cookie': 'session=' + session}, verify=False)
        return resp.content

    # pylint: disable=too-many-statements
    def test_csr(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_certificate_settings()

        # Check bad country input
        self.settings_page.open_generate_csr_modal()
        self._fill_csr_request(bad_country=True)
        self.settings_page.click_modal_approve()
        self.settings_page.wait_for_toaster('Country must be only 2 letters')
        self.settings_page.safe_refresh()

        # Check other bad input and create csr at the end
        self.settings_page.click_certificate_settings()
        self.settings_page.open_generate_csr_modal()
        self._fill_csr_request(initial=True)
        self.settings_page.click_modal_approve()
        self.settings_page.wait_for_toaster('CSR created successfully')

        # Check all details are correct
        assert self.settings_page.find_element_by_text(
            'US/New York/New York City/Axonius, Inc/axonius/contact@axonius.com')
        assert self.settings_page.find_element_by_text('CF:3B:18:67:81:1F:20:64:CB:65:A6:23:A2:0C:B1:1A:2C:43:E4:89')
        assert self.settings_page.find_element_by_text('shukka.com')

        # Check cancel works
        self.settings_page.click_cancel_csr()
        self.settings_page.wait_for_toaster('CSR deleted successfully')
        with pytest.raises(NoSuchElementException):
            self.settings_page.click_cancel_csr()
        assert self.settings_page.find_element_parent_by_text('None')

        self.settings_page.open_generate_csr_modal()
        self._fill_csr_request()
        self.settings_page.click_modal_approve()
        self.settings_page.wait_for_toaster('CSR created successfully')

        csr_file = self._get_csr_file()
        with open('cert.csr', 'wb') as fh:
            fh.write(csr_file)

        # Generate rootCA key
        os.system('openssl genrsa -out rootCA.key 4096')
        # Create rootCA Certificate - this command works only on posix machines or WSL on windows
        os.system('echo -e "\n\n\n\n\n\n\n" | openssl req -x509 -new -nodes -key rootCA.key -sha256'
                  ' -days 1024 -out rootCA.crt')
        # Sign the csr with our rootCA
        os.system('openssl x509 -req -in cert.csr -CA rootCA.crt -CAkey rootCA.key -CAcreateserial -out cert.crt '
                  '-days 500 -sha256')

        with open('cert.crt', 'r') as fh:
            cert_file = fh.read()

        with open('rootCA.crt', 'r') as fh:
            rootCA_file = fh.read()

        # Check bad certificate upload
        self.settings_page.open_import_sign_csr_modal()
        self.settings_page.upload_file_by_id('cert_file', rootCA_file)
        self.settings_page.click_modal_approve()
        self.settings_page.wait_for_toaster('Certificate does not match private key on server')

        # Upload good certificate
        self.settings_page.open_import_sign_csr_modal()
        self.settings_page.upload_file_by_id('cert_file', cert_file)
        self.settings_page.click_modal_approve()
        self.settings_page.wait_for_toaster('Certificate was added successfully')

        self.settings_page.refresh()
        self.settings_page.click_certificate_settings()
        assert self.settings_page.find_element_parent_by_text('None')
        assert self.settings_page.find_element_parent_by_text('AU/Some-State/Internet Widgits Pty Ltd')

        time.sleep(3)
        peercert = _get_peer_ssl('https://localhost', False)
        # In this path, we check that the certificate is good
        peercert_parsed = dict(i[0] for i in peercert['subject'])
        assert peercert_parsed['commonName'] == 'shukka.com'

        # Cleanup at the end
        self.settings_page.switch_to_page()
        self.settings_page.click_certificate_settings()
        self.settings_page.click_reset_to_defaults()
        os.system('rm -f rootCA.key rootCA.crt cert.csr cert.crt rootCA.srl')
