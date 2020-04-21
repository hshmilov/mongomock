from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase


class TestUserUpdate(TestBase):

    def test_user_update_new_password(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.wait_for_table_to_be_responsive()
        self.settings_page.create_new_user(ui_consts.UPDATE_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.VIEWER_ROLE)

        self.settings_page.update_new_user(username=ui_consts.UPDATE_USERNAME,
                                           password=ui_consts.UPDATE_PASSWORD,
                                           first_name=ui_consts.UPDATE_FIRST_NAME,
                                           last_name=ui_consts.UPDATE_LAST_NAME)

        self.settings_page.wait_for_user_updated_toaster()

        all_users = self.settings_page.get_all_users_data()
        update_user_list = list(filter(lambda user:
                                       user.first_name == ui_consts.UPDATE_FIRST_NAME
                                       and user.last_name == ui_consts.UPDATE_LAST_NAME,
                                       all_users))
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
                                           self.settings_page.VIEWER_ROLE)

        self.settings_page.update_new_user(username=ui_consts.UPDATE_USERNAME,
                                           first_name=ui_consts.UPDATE_FIRST_NAME,
                                           last_name=ui_consts.UPDATE_LAST_NAME)
        self.settings_page.wait_for_user_updated_toaster()
        self.settings_page.wait_for_user_updated_toaster_to_end()

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
                                           ui_consts.LAST_NAME,
                                           self.settings_page.RESTRICTED_ROLE)

        self.settings_page.wait_for_user_created_toaster()
        self.settings_page.click_edit_user(ui_consts.UPDATE_USERNAME)
        self.settings_page.fill_password_field('')
        assert self.settings_page.is_save_button_disabled()
