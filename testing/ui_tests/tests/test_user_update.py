import pytest

from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase

from services.axon_service import TimeoutException


class TestUserUpdate(TestBase):

    def test_user_update_new_password(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.UPDATE_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.READ_ONLY_ROLE)

        self.settings_page.update_new_user(username=ui_consts.UPDATE_USERNAME,
                                           password=ui_consts.UPDATE_PASSWORD,
                                           first_name=ui_consts.UPDATE_FIRST_NAME,
                                           last_name=ui_consts.UPDATE_LAST_NAME)

        self.settings_page.wait_for_toaster('User updated.')
        self.settings_page.wait_for_toaster_to_end('User updated.')

        all_users = list(self.settings_page.get_all_users_from_users_and_roles())
        user_full_name = f'{ui_consts.UPDATE_FIRST_NAME} {ui_consts.UPDATE_LAST_NAME}'
        update_user_list = list(filter(lambda user: user_full_name in user, all_users))
        assert len(update_user_list) == 1

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.UPDATE_USERNAME, password=ui_consts.UPDATE_PASSWORD)

        self.reports_page.switch_to_page()
        assert self.reports_page.is_disabled_new_report_button()

    def test_user_update_without_password(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.UPDATE_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.READ_ONLY_ROLE)

        self.settings_page.update_new_user(username=ui_consts.UPDATE_USERNAME,
                                           first_name=ui_consts.UPDATE_FIRST_NAME,
                                           last_name=ui_consts.UPDATE_LAST_NAME)
        self.settings_page.wait_for_toaster('User updated.')
        self.settings_page.wait_for_toaster_to_end('User updated.')

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.UPDATE_USERNAME, password=ui_consts.NEW_PASSWORD)

        self.reports_page.switch_to_page()
        assert self.reports_page.is_disabled_new_report_button()

    def test_user_update_with_empty_password(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.UPDATE_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME)

        self.settings_page.wait_for_user_created_toaster()
        self.settings_page.click_edit_user(ui_consts.UPDATE_USERNAME)
        self.settings_page.fill_password_field('')
        with pytest.raises(TimeoutException):
            self.settings_page.click_update_user()
        assert not self.settings_page.is_update_button_enabled()
