import re
from datetime import datetime, timedelta

from services.standalone_services.maildiranasaurus_service import MaildiranasaurusService
from services.standalone_services.smtp_service import generate_random_valid_email
from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase


def _validate_link_in_email_body(smtp_service, recipient, link):
    smtp_service.verify_email_send(recipient)
    mail_content = smtp_service.get_email_body(recipient)
    urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                      str(mail_content[0]))
    assert urls[0] == link


class TestUserResetPassword(TestBase):
    NEW_USER_PASSWORD = '123456'

    def test_new_user_with_reset_password_link(self):
        with MaildiranasaurusService().contextmanager(take_ownership=True) as smtp_service:
            self.settings_page.add_email_server(smtp_service.fqdn, smtp_service.port)
            recipient = generate_random_valid_email()
            # create new admin user with reset password link
            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()
            self.settings_page.wait_for_table_to_be_responsive()
            self.settings_page.create_new_user(ui_consts.UPDATE_USERNAME,
                                               ui_consts.NEW_PASSWORD,
                                               ui_consts.FIRST_NAME,
                                               ui_consts.LAST_NAME,
                                               self.settings_page.ADMIN_ROLE,
                                               generate_password=True)
            self.settings_page.wait_for_reset_password_form()
            # get the link from the modal vie copy button
            link = self.settings_page.get_reset_password_link()
            self.settings_page.fill_email_and_click_reset_password_link(recipient)
            self.settings_page.close_reset_password_modal()
            # validate email
            _validate_link_in_email_body(smtp_service, recipient, link)
            # reset link
            self._reset_password_via_link(link)
            self._reset_password_via_link_check_expired(link)
            self._login_after_expired_msg()

        self.settings_page.remove_email_server()

    def test_user_update_with_reset_password_link(self):
        with MaildiranasaurusService().contextmanager(take_ownership=True) as smtp_service:
            self.settings_page.add_email_server(smtp_service.fqdn, smtp_service.port)
            recipient = generate_random_valid_email()
            # creat new user with regular password
            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()
            self.settings_page.wait_for_table_to_be_responsive()
            self.settings_page.create_new_user(ui_consts.UPDATE_USERNAME,
                                               ui_consts.NEW_PASSWORD,
                                               ui_consts.FIRST_NAME,
                                               ui_consts.LAST_NAME,
                                               self.settings_page.ADMIN_ROLE)
            # edit the user to get the link
            link = self.settings_page.edit_user_and_get_reset_password_link(ui_consts.UPDATE_USERNAME)
            self.settings_page.fill_email_and_click_reset_password_link(recipient)
            self.settings_page.close_reset_password_modal()
            # validate email
            _validate_link_in_email_body(smtp_service, recipient, link)
            # reset link
            self._reset_password_via_link(link)
            self._reset_password_via_link_check_expired(link)
            self._login_after_expired_msg()

        self.settings_page.remove_email_server()

    def test_user_expired_password(self):
        self.settings_page.add_user(ui_consts.NOTES_USERNAME,
                                    ui_consts.NEW_PASSWORD,
                                    ui_consts.FIRST_NAME,
                                    ui_consts.LAST_NAME,
                                    self.settings_page.ADMIN_ROLE)
        # change last password change
        self.axonius_system.db.gui_users_collection().update_many(
            {'user_name': {'$ne': 'admin'}},
            {'$set': {'password_last_updated': datetime.utcnow() - timedelta(days=10)}}
        )

        self.login_page.switch_user(ui_consts.NOTES_USERNAME, ui_consts.NEW_PASSWORD)

        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.click_toggle_button(self.settings_page.find_password_expiration_toggle(), make_yes=True)
        self.settings_page.fill_password_expiration_days_field(10)
        self.settings_page.click_save_global_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

        self.login_page.switch_user(ui_consts.NOTES_USERNAME, ui_consts.NEW_PASSWORD,
                                    wait_for_successfull_login=False)
        self.login_page.wait_for_password_expired_warning()
        self.login_page.click_ant_button('OK')
        self.reset_password_page.wait_for_reset_password_page_to_load()

        self.reset_password_page.set_new_password(ui_consts.NEW_PASSWORD)
        assert self.reset_password_page.wait_for_password_differ_message()

        self.reset_password_page.set_new_password(ui_consts.UPDATE_PASSWORD)
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(ui_consts.NOTES_USERNAME, ui_consts.UPDATE_PASSWORD)

        self.login_page.logout_and_login_with_admin()
        # disable settings
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.click_toggle_button(self.settings_page.find_password_expiration_toggle(), make_yes=False)
        self.settings_page.click_save_global_settings()
        self.settings_page.wait_for_saved_successfully_toaster()
        # revert affected users
        self.axonius_system.db.gui_users_collection().update_many(
            {'user_name': {'$ne': 'admin'}},
            {'$set': {'password_last_updated': datetime.utcnow()}}
        )

    def _reset_password_via_link(self, link):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.reset_password_page.reset_password_via_link(link, self.NEW_USER_PASSWORD)
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.UPDATE_USERNAME, password=self.NEW_USER_PASSWORD)

    def _reset_password_via_link_check_expired(self, link):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.driver.get(link)
        self.reset_password_page.wait_for_expired_msg()

    def _login_after_expired_msg(self):
        # revert state for next test
        self.driver.get(self.base_url)
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(DEFAULT_USER['user_name'], DEFAULT_USER['password'])
