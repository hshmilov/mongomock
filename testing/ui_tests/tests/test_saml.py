import time
import urllib
import pathlib
import tempfile
import contextlib
import collections
from uuid import uuid4

import docker
import requests
import netifaces

from axonius.consts.gui_consts import PREDEFINED_ROLE_RESTRICTED, PREDEFINED_ROLE_VIEWER
from ui_tests.tests.permissions_test_base import PermissionsTestBase


# pylint: disable=inconsistent-mro


SamlServer = collections.namedtuple(
    'SamlServer', 'test_user_name test_user_password metadata_url name test_givenname test_surname')

TEST_GIVENNAME = 'test_givenname'
TEST_SURNAME = 'test_surname'


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
                             name='saml-poc', test_givenname=TEST_GIVENNAME, test_surname=TEST_SURNAME)

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


class TestSaml(PermissionsTestBase):

    @staticmethod
    def _extract_saml_and_internal_user_with_name(all_users, username):
        relevant_users = [u for u in all_users if username in u.user_name]
        assert len(relevant_users) == 2, f'Expected two users with name: {username}'

        saml_user = [u for u in relevant_users if u.source.lower() == 'saml'][0]
        internal_user = [u for u in relevant_users if u.source.lower() == 'internal'][0]

        return saml_user, internal_user

    def test_saml_user_added(self):
        with create_saml_server(self.base_url) as saml_server:
            self.settings_page.set_saml(saml_server.name, saml_server.metadata_url, '', PREDEFINED_ROLE_VIEWER)
            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()

            # Set the devices page path in the url
            self.driver.get(self.devices_page.url)
            self.login_page.login_with_saml_server(saml_server)

            # Make sure that after logging in, we are redirected to the devices page
            assert self.driver.current_url == self.devices_page.url
            self.login_page.logout()

            self.login()
            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()

            assert self.settings_page.fetch_saml_user().user_name

    def test_saml_role_assignment_rules(self):
        self.base_page.run_discovery()
        with create_saml_server(self.base_url) as saml_server:
            self.settings_page.set_saml(saml_server.name,
                                        saml_server.metadata_url,
                                        '',
                                        None,
                                        True,
                                        [
                                            {
                                                'key': 'surname',
                                                'value': TEST_SURNAME,
                                                'role': PREDEFINED_ROLE_VIEWER
                                            }
                                        ])

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login_with_saml_server(saml_server)

            # Making sure we are indeed logged in
            self.account_page.switch_to_page()
            for screen in self.get_all_screens():
                assert not screen.is_switch_button_disabled()
                screen.switch_to_page()
            self._assert_viewer_role()

            self.login_page.logout()

            self.login()
            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()

            saml_user = self.settings_page.fetch_saml_user()
            assert saml_user.user_name
            assert saml_user.role == PREDEFINED_ROLE_VIEWER

            self.settings_page.switch_to_page()
            self.settings_page.click_identity_providers_settings()
            self.settings_page.fill_saml_assignment_rule('surname', 'wrong', PREDEFINED_ROLE_VIEWER, 1)
            self.settings_page.click_add_assignment_rule()
            self.settings_page.fill_saml_assignment_rule('surname', TEST_SURNAME, PREDEFINED_ROLE_RESTRICTED, 2)
            self.settings_page.click_save_identity_providers_settings()
            self.settings_page.wait_for_saved_successfully_toaster()
            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.click_login_with_saml()
            self.account_page.switch_to_page()
            for screen in self.get_all_screens():
                assert screen.is_switch_button_disabled()

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

            self.settings_page.set_saml(saml_server.name,
                                        saml_server.metadata_url,
                                        default_role_name=saml_users_role_name)

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()

            self.login_page.login_with_saml_server(saml_server)
            self.account_page.switch_to_page()
            self.account_page.wait_for_spinner_to_end()
            actual_saml_user_initial_api_key_and_secret = self.account_page.get_api_key_and_secret()

            self.login_page.logout()

            self.login()
            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()

            saml_user_initial_snapshot = self.settings_page.fetch_saml_user()
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

            self.account_page.switch_to_page()
            self.account_page.change_password(
                initial_internal_user_password,
                new_internal_user_password,
                new_internal_user_password,
                self.account_page.wait_for_password_changed_toaster)

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

        self.settings_page.set_saml('saml_name',
                                    'https://saml_metadata_url',
                                    external_url_test,
                                    PREDEFINED_ROLE_RESTRICTED)

        time.sleep(10)  # Allow settings to apply
        response = requests.get(urllib.parse.urljoin('https://127.0.0.1', '/api/login/saml/metadata'))
        response.raise_for_status()

        expected_url = urllib.parse.urljoin(external_url_test, '/api/login/saml/?acs')
        assert expected_url in response.text
