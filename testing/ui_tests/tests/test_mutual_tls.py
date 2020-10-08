import json
import os
import re
import subprocess
import time
import urllib.parse

import OpenSSL
import requests

from axonius.consts.gui_consts import GUI_CONFIG_NAME
from services.plugins.gui_service import GuiService
from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.tests.test_global_ssl import CERT_SUCCESS_TOASTER_MSG
from ui_tests.tests.ui_test_base import TestBase

NOT_PEM_FORMAT_ERROR_MSG = 'The uploaded file is not a pem-format certificate'
NO_MUTUAL_CERTIFICATE_PROVIDED_MSG = 'Client certificate not found in request. ' \
                                     'Please make sure your client uses a certificate to access Axonius'
MUTUAL_TLS_SETTING_WITH_ENFORCE = {'ssl_trust': {'ca_files': [], 'enabled': False},
                                   'mutual_tls': {'ca_certificate': {'uuid': '{uuid}', 'filename': '{filename}'},
                                                  'enabled': True, 'mandatory': True}}
NO_CLIENT_CERTIFICATE_ERROR = 'Client certificate not found in request. ' \
                              'Please make sure your client uses a certificate to access Axonius'

CURL_SCRIPT_PATH = os.path.join(os.getcwd(), 'set_settings.sh')
CURL_SET_ENFORCE_CMD = '''#!/bin/bash
curl 'https://127.0.0.1/api/certificate/certificate_settings' \\
  -H 'authority: 127.0.0.1' \\
  -H 'accept: application/json, text/plain, */*' \\
  -H 'x-csrf-token: {csrf_token}' \\
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'\\
  -H 'content-type: application/json;charset=UTF-8' \\
  -H 'origin: https://127.0.0.1' \\
  -H 'sec-fetch-site: same-origin' \\
  -H 'sec-fetch-mode: cors' \\
  -H 'sec-fetch-dest: empty' \\
  -H 'referer: https://127.0.0.1/settings' \\
  -H 'accept-language: en-US,en;q=0.9,he;q=0.8' \\
  -H 'X-CLIENT-ESCAPED-CERT: {cert_file}' \\
  -H 'cookie: session={session}' \\
  --data-binary '{{"ssl_trust":{{"ca_files":[],"enabled":false}},"mutual_tls":{{"ca_certificate":{{"uuid":"{uuid}","filename":"{filename}"}},"enabled":true,"mandatory":{status}}}}}' \\
  --compressed \\
  --insecure \\
  --key test.key \\
  --cert test.crt'''


class TestMutualTLS(TestBase):
    # pylint: disable=too-many-statements
    def test_mutual_tls(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_certificate_settings()
        # Generate key pair
        key = OpenSSL.crypto.PKey()
        key.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)
        key_pem = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key)

        # Generate CSR
        cert = OpenSSL.crypto.X509()
        cert.get_subject().CN = 'test.com'
        cert.set_serial_number(11893419192028291059)
        cert.set_version(2)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        base_constraints = [OpenSSL.crypto.X509Extension(b'subjectAltName', False,
                                                         b'DNS:test.com,DNS:www.test.net,IP:10.0.0.1')]
        cert.add_extensions(base_constraints)
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')
        cert_file = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        with open('test.crt', 'wb') as fh:
            fh.write(cert_file)
        with open('test.key', 'wb') as fh:
            fh.write(key_pem)

        self.settings_page.set_mutual_tls(b'aaaaaaaaaaaaaaa')
        self.settings_page.save_and_wait_for_toaster(toaster_message=NOT_PEM_FORMAT_ERROR_MSG)

        self.settings_page.hard_refresh()
        self.settings_page.click_certificate_settings()
        fname = self.settings_page.set_mutual_tls(cert_file)
        self.settings_page.save_and_wait_for_toaster(toaster_message=CERT_SUCCESS_TOASTER_MSG)

        self.settings_page.set_enforce_mutual_tls()
        self.settings_page.save_and_wait_for_toaster(toaster_message=NO_MUTUAL_CERTIFICATE_PROVIDED_MSG)

        session = requests.session()
        session, session_id = self.do_login(session)
        csrf_token = self.get_csrf_token(session)
        uuid = self.axonius_system.db.plugins.gui.configurable_configs.get_all().get(GUI_CONFIG_NAME, {}).\
            get('mutual_tls_settings', {}).get('ca_certificate', {}).get('uuid', '')
        MUTUAL_TLS_SETTING_WITH_ENFORCE['mutual_tls']['ca_certificate']['uuid'] = uuid
        MUTUAL_TLS_SETTING_WITH_ENFORCE['mutual_tls']['ca_certificate']['filename'] = fname

        resp = session.post('https://127.0.0.1/api/certificate/certificate_settings',
                            verify=False,
                            headers={'Content-Type': 'application/json;charset=UTF-8', 'X-CSRF-TOKEN': csrf_token},
                            data=json.dumps(MUTUAL_TLS_SETTING_WITH_ENFORCE))
        assert resp.json().get('message', '') == NO_CLIENT_CERTIFICATE_ERROR

        # Set enforcement to true
        csrf_token = self.get_csrf_token(session)
        with open(CURL_SCRIPT_PATH, 'w') as fh:
            fh.write(
                CURL_SET_ENFORCE_CMD.format(csrf_token=csrf_token,
                                            uuid=uuid,
                                            filename=fname,
                                            session=session_id,
                                            cert_file=urllib.parse.quote(cert_file), status='true').replace('\\\n', ''))
        os.chmod(CURL_SCRIPT_PATH, 0o777)
        output = subprocess.check_output(['bash', CURL_SCRIPT_PATH])
        assert b'true' in output

        # make sure certificate is required
        resp = requests.get('https://127.0.0.1/login', verify=False)
        assert resp.status_code == 400

        # Set enforcement to false
        self.axonius_system.db.plugins.gui.configurable_configs.update_config(
            GUI_CONFIG_NAME,
            {'mutual_tls_settings.mandatory': False},
            upsert=True
        )
        gs = GuiService()
        gs.take_process_ownership()
        gs.restart()
        time.sleep(30)
        # Make sure everything got back to normal
        resp = requests.get('https://127.0.0.1/login', verify=False)
        assert resp.status_code == 200

        os.remove('test.key')
        os.remove('test.crt')
        os.remove(CURL_SCRIPT_PATH)

    @staticmethod
    def do_login(session):
        resp = session.post('https://127.0.0.1/api/login',
                            data=json.dumps({'user_name': DEFAULT_USER['user_name'],
                                             'password': DEFAULT_USER['password'], 'remember_me': False}),
                            verify=False)
        session_id = re.findall('session=(.*?);', resp.headers['Set-Cookie'])[0]
        resp.close()
        return session, session_id

    @staticmethod
    def get_csrf_token(session):
        return session.get('https://127.0.0.1/api/csrf', verify=False).text
