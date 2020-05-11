import urllib
import pathlib
import tempfile
import contextlib
import collections
from uuid import uuid4

import docker
import requests
import netifaces

from ui_tests.tests.ui_test_base import TestBase


SamlServer = collections.namedtuple(
    'SamlServer', 'test_user_name test_user_password metadata_url name test_givenname test_surname')


def _docker_host_address():
    # This sucks and doesn't really belong here, I don't know where it should reside.
    # We use it so Axonius will be able to access our identity provider.

    # Output of netifaces.gateways()['default'] looks like
    # {2: ('192.168.43.1', 'en0')}

    # pylint: disable = I1101
    default_interface_name = netifaces.gateways()['default'][netifaces.AF_INET][1]
    return netifaces.ifaddresses(default_interface_name)[netifaces.AF_INET][0]['addr']


@contextlib.contextmanager
def create_saml_server(base_url):
    server_data = SamlServer(test_user_name='user1', test_user_password='user1pass',
                             metadata_url=f'http://{_docker_host_address()}:8080/simplesaml/saml2/idp/metadata.php',
                             name='saml-poc', test_givenname='test_givenname', test_surname='test_surname')

    authsources_data = f'''<?php

$config = array(

    'admin' => array(
        'core:AdminPassword',
    ),

    'example-userpass' => array(
        'exampleauth:UserPass',
        '{server_data.test_user_name}:{server_data.test_user_password}' => array(
            'uid' => array('1'),
            'eduPersonAffiliation' => array('group1'),
            'email' => 'user1@example.com',
            'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname' => '{server_data.test_surname}',
            'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname' => '{server_data.test_givenname}',
        ),
    ),
);
'''

    with tempfile.TemporaryDirectory(dir='/tmp') as temporary_directory:
        authsources_path = pathlib.Path(temporary_directory).joinpath('authsources.php')
        authsources_path.write_text(authsources_data)

        volumes = {str(authsources_path): {'bind': '/var/www/simplesamlphp/config/authsources.php', 'mode': 'rw'}}

        environment = {'SIMPLESAMLPHP_SP_ENTITY_ID': f'{base_url}/api/login/saml/metadata/',
                       'SIMPLESAMLPHP_SP_ASSERTION_CONSUMER_SERVICE': f'{base_url}/api/login/saml/?acs',
                       'SIMPLESAMLPHP_SP_SINGLE_LOGOUT_SERVICE': f'{base_url}/api/logout/'}

        ports = {8080: 8080, 8443: 8443}

        docker_client = docker.from_env()
        container = docker_client.containers.run('kristophjunge/test-saml-idp',
                                                 ports=ports, environment=environment, volumes=volumes, detach=True)

        try:
            yield server_data
        finally:
            container.remove(v=True, force=True)


class TestSaml(TestBase):
    def _simple_samlserver_page_login(self, saml_server):
        # This method deals with a page served by the saml server docker container.
        # It is a page, and thus one might be tempted to create a Page class and file for it
        # I think that it is so tightly coupled to this container and code that it will cause
        # more confusion and won't reduce complexity.

        self.base_page.wait_for_element_present_by_text('A service has requested you to authenticate yourself.')
        self.base_page.fill_text_field_by_element_id('username', saml_server.test_user_name)
        self.base_page.fill_text_field_by_element_id('password', saml_server.test_user_password)
        self.base_page.find_element_by_text('Login').click()

    def _set_saml(self, name, metadata_url, external_url='', default_role_name=None):
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.set_allow_saml_based_login()
        self.settings_page.fill_saml_idp(name)
        self.settings_page.fill_saml_metadata_url(metadata_url)
        self.settings_page.fill_saml_axonius_external_url(external_url=external_url)
        if default_role_name:
            self.settings_page.set_default_role_id(default_role_name)
        self.settings_page.click_save_gui_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

    def _login_with_saml(self, saml_server):
        self.login_page.wait_for_login_page_to_load()
        self.login_page.click_login_with_saml()
        self._simple_samlserver_page_login(saml_server)

    def _fetch_saml_user(self):
        all_users = self.settings_page.get_all_users_data()
        valid_users = [u for u in all_users if u.source.lower() == 'saml']
        assert len(valid_users) == 1, 'Got more or less than expected valid saml usernames'
        return valid_users[0]

    @staticmethod
    def _extract_saml_and_internal_user_with_name(all_users, username):
        relevant_users = [u for u in all_users if username in u.user_name]
        assert len(relevant_users) == 2, f'Expected two users with name: {username}'

        saml_user = [u for u in relevant_users if u.source.lower() == 'saml'][0]
        internal_user = [u for u in relevant_users if u.source.lower() == 'internal'][0]

        return saml_user, internal_user

    def test_saml_user_added(self):
        with create_saml_server(self.base_url) as saml_server:
            self._set_saml(saml_server.name, saml_server.metadata_url)

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self._login_with_saml(saml_server)

            self.login_page.logout()

            self.login()
            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()

            assert self._fetch_saml_user().user_name

    # pylint: disable=R0915
    def test_saml_same_username(self):
        saml_devices_permissions = {
            'dashboard': [
                'View dashboard',
            ],
            'settings': [
                'Reset API Key',
            ],
            'devices_assets': [
                'View devices',
                'Edit devices',
                'Run saved queries',
                'Edit saved queries',
                'Delete saved query',
                'Create saved query',
            ]
        }

        saml_users_permissions = {
            'dashboard': [
                'View dashboard',
            ],
            'settings': [
                'Reset API Key',
            ],
            'devices_assets': [
                'View devices',
                'Edit devices',
                'Run saved queries',
                'Edit saved queries',
                'Delete saved query',
                'Create saved query',
            ]
        }

        with create_saml_server(self.base_url) as saml_server:
            self.settings_page.switch_to_page()
            self.settings_page.click_manage_roles_settings()
            saml_users_role_name = f'{uuid4().hex[:15]} role'
            self.settings_page.wait_for_table_to_load()
            self.settings_page.create_new_role(saml_users_role_name, saml_users_permissions)

            self._set_saml(saml_server.name, saml_server.metadata_url, default_role_name=saml_users_role_name)

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()

            self._login_with_saml(saml_server)
            self.account_page.switch_to_page()
            self.account_page.wait_for_spinner_to_end()
            actual_saml_user_initial_api_key_and_secret = self.account_page.get_api_key_and_secret()

            self.login_page.logout()

            self.login()
            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()

            saml_user_initial_snapshot = self._fetch_saml_user()
            saml_username = saml_user_initial_snapshot.user_name

            initial_internal_user_password = 'PASSWORD1'
            new_internal_user_password = 'password2'

            self.settings_page.create_new_user_with_new_permission(saml_username, initial_internal_user_password,
                                                                   saml_server.test_givenname, saml_server.test_surname,
                                                                   saml_devices_permissions)

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=saml_username, password=initial_internal_user_password,
                                  wait_for_getting_started=False)

            self.my_account_page.switch_to_page()
            self.my_account_page.change_password(
                initial_internal_user_password,
                new_internal_user_password,
                new_internal_user_password,
                self.my_account_page.wait_for_password_changed_toaster)

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=saml_username, password=new_internal_user_password,
                                  wait_for_getting_started=False)

            self.account_page.switch_to_page()
            self.account_page.wait_for_spinner_to_end()

            created_user_initial_api_key_and_secret = self.account_page.get_api_key_and_secret()
            self.account_page.reset_api_key_and_secret()

            created_user_new_api_key_and_secret = self.account_page.get_api_key_and_secret()

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login()

            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()

            all_users = self.settings_page.get_all_users_data()

            saml_user, internal_user = self._extract_saml_and_internal_user_with_name(all_users, saml_username)

            self.settings_page.click_manage_roles_settings()

            self.settings_page.match_role_permissions(saml_user.role, saml_users_permissions)

            self.settings_page.match_role_permissions(saml_user.role, saml_devices_permissions)

            assert created_user_new_api_key_and_secret != actual_saml_user_initial_api_key_and_secret
            assert created_user_new_api_key_and_secret != created_user_initial_api_key_and_secret
            assert created_user_initial_api_key_and_secret != actual_saml_user_initial_api_key_and_secret

    def test_metadata_contains_valid_external_url(self):
        external_url_test = 'https://i.am.just.a.placeholder'

        self._set_saml('saml_name', 'https://saml_metadata_url', external_url_test)

        response = requests.get(urllib.parse.urljoin('https://127.0.0.1', '/api/login/saml/metadata'))
        response.raise_for_status()

        expected_url = urllib.parse.urljoin(external_url_test, '/api/login/saml/?acs')
        assert expected_url in response.text
