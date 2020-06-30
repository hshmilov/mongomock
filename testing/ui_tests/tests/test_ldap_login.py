from ui_tests.tests.permissions_test_base import PermissionsTestBase

from axonius.consts.gui_consts import PREDEFINED_ROLE_RESTRICTED, LDAP_GROUP, PREDEFINED_ROLE_ADMIN, EMAIL_ADDRESS, \
    EMAIL_DOMAIN, PREDEFINED_ROLE_VIEWER
from test_credentials.test_ad_credentials import ad_client1_details, GROUPS_USERS, ad_client1_mail


def _get_domain_and_username(client_details):
    return client_details['user'].split('\\')


class TestLDAPLogin(PermissionsTestBase):
    def test_ldap_login(self):
        self._set_ldap(ad_client1_details['dc_name'], role_name=PREDEFINED_ROLE_RESTRICTED)
        domain, username = _get_domain_and_username(ad_client1_details)
        self._logout_and_login_with_ldap(username + 'bad',
                                         ad_client1_details['password'],
                                         domain)
        assert self.login_page.find_failed_ad_login_msg()

        self.login_page.fill_ldap_login_details(username=username,
                                                password=ad_client1_details['password'],
                                                domain=domain)
        self.login_page.click_login_button()

        # Making sure we are indeed logged in
        self.account_page.switch_to_page()

        for screen in self.get_all_screens():
            screen.assert_screen_is_restricted()

    def test_ldap_login_with_groups(self):
        self._set_ldap(ad_client1_details['dc_name'], GROUPS_USERS['group'], PREDEFINED_ROLE_RESTRICTED)
        domain, username = _get_domain_and_username(ad_client1_details)
        self._logout_and_login_with_ldap(username,
                                         ad_client1_details['password'],
                                         domain)
        assert self.login_page.find_failed_ad_login_msg_group(GROUPS_USERS['group'])

        domain, username = GROUPS_USERS['user'].split('\\')
        self.login_page.fill_ldap_login_details(username=username,
                                                password=ad_client1_details['password'],
                                                domain=domain)
        self.login_page.click_login_button()

        # Making sure we are indeed logged in
        self.account_page.switch_to_page()

        for screen in self.get_all_screens():
            screen.assert_screen_is_restricted()

    def test_ldap_login_with_rules(self):
        self._set_ldap(ad_client1_details['dc_name'])
        domain, username = _get_domain_and_username(ad_client1_details)
        self._logout_and_login_with_ldap(username,
                                         ad_client1_details['password'],
                                         domain)
        self.login_page.wait_for_no_permissions_message()

        self.login()
        self.settings_page.switch_to_page()
        self.settings_page.click_identity_providers_settings()
        self.settings_page.wait_for_spinner_to_end()

        self.settings_page.click_add_assignment_rule()
        self.settings_page.fill_ldap_assignment_rule(LDAP_GROUP, 'Administrators', PREDEFINED_ROLE_RESTRICTED)

        self.settings_page.click_save_identity_providers_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

        self._logout_and_login_with_ldap(username,
                                         ad_client1_details['password'],
                                         domain)
        self.login_page.wait_for_no_permissions_message()

        self.login()
        self.settings_page.switch_to_page()
        self.settings_page.click_identity_providers_settings()
        self.settings_page.wait_for_spinner_to_end()
        self.settings_page.set_evaluate_role_on_new_and_existing_users()
        self.settings_page.click_save_identity_providers_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

        self._logout_and_login_with_ldap(username,
                                         ad_client1_details['password'],
                                         domain)
        self.login_page.make_getting_started_disappear()
        # Making sure we are indeed logged in
        self.account_page.switch_to_page()

        for screen in self.get_all_screens():
            screen.assert_screen_is_restricted()

        self.login_page.logout()

    def test_ldap_login_with_email_rule(self):
        self._set_ldap(ad_client1_details['dc_name'], rules=[{
            'type': EMAIL_ADDRESS,
            'value': ad_client1_mail,
            'role_name': PREDEFINED_ROLE_RESTRICTED,
        }])
        domain, username = _get_domain_and_username(ad_client1_details)
        self._logout_and_login_with_ldap(username,
                                         ad_client1_details['password'],
                                         domain)
        self.login_page.make_getting_started_disappear()
        # Making sure we are indeed logged in
        self.account_page.switch_to_page()

        for screen in self.get_all_screens():
            screen.assert_screen_is_restricted()

    def test_ldap_login_with_email_domain_rule(self):
        self._set_ldap(ad_client1_details['dc_name'], rules=[{
            'type': EMAIL_DOMAIN,
            'value': ad_client1_mail.split('@')[1],
            'role_name': PREDEFINED_ROLE_RESTRICTED,
        }])
        domain, username = _get_domain_and_username(ad_client1_details)
        self._logout_and_login_with_ldap(username,
                                         ad_client1_details['password'],
                                         domain)
        self.login_page.make_getting_started_disappear()
        # Making sure we are indeed logged in
        self.account_page.switch_to_page()

        for screen in self.get_all_screens():
            screen.assert_screen_is_restricted()

    def test_two_assignment_rules(self):
        domain, username = _get_domain_and_username(ad_client1_details)
        self.base_page.run_discovery()
        self._set_ldap(ad_client1_details['dc_name'],
                       evaluate_role_on_every_login=True,
                       rules=[{
                           'type': LDAP_GROUP,
                           'value': 'bla bla',
                           'role_name': PREDEFINED_ROLE_RESTRICTED
                       }, {
                           # Check that partial domain name will not be use
                           'type': LDAP_GROUP,
                           'value': 'Domain',
                           'role_name': PREDEFINED_ROLE_ADMIN
                       }, {
                           'type': LDAP_GROUP,
                           'value': 'Administrators',
                           'role_name': PREDEFINED_ROLE_VIEWER
                       }])

        self._logout_and_login_with_ldap(username, ad_client1_details['password'], domain)
        self.login_page.make_getting_started_disappear()
        # Making sure we are indeed logged in
        self._assert_viewer_role()

    def _set_ldap(self,
                  dc_address,
                  group_ldap=None,
                  role_name=None,
                  rules=None,
                  evaluate_role_on_every_login=False):
        self.settings_page.switch_to_page()
        self.settings_page.click_identity_providers_settings()
        self.settings_page.wait_for_spinner_to_end()
        toggle = self.settings_page.find_allow_ldap_logins_toggle()
        self.settings_page.click_toggle_button(toggle, scroll_to_toggle=False)
        self.settings_page.fill_dc_address(dc_address)
        if group_ldap:
            self.settings_page.fill_group_ldap(group_ldap)
        if role_name:
            self.settings_page.select_default_role(role_name)
        if evaluate_role_on_every_login:
            self.settings_page.set_evaluate_role_on_new_and_existing_users()
        if rules:
            rule_index = 1
            for rule in rules:
                self.settings_page.click_add_assignment_rule()
                self.settings_page.fill_ldap_assignment_rule(rule.get('type'), rule.get('value'), rule.get('role_name'),
                                                             rule_index)
                rule_index += 1
        self.settings_page.click_save_identity_providers_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

    def _logout_and_login_with_ldap(self, username, password, domain):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.click_login_with_ldap()
        self.login_page.wait_for_spinner_to_end()
        self.login_page.fill_ldap_login_details(username=username,
                                                password=password,
                                                domain=domain)
        self.login_page.click_login_button()
