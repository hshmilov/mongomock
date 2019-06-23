import time

import pytest
from selenium.common.exceptions import NoSuchElementException

from test_credentials.test_gui_credentials import AXONIUS_USER
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.pages.enforcements_page import Action, ActionCategory
from axonius.utils.wait import wait_until
from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG


class TestFeatureFlags(TestBase):

    ACTION_TO_LOCK = Action.create_jira_incident.value
    ACTION_TO_UNLOCK = Action.cybereason_isolate.value

    def test_feature_flags_axonius_user(self):
        self.devices_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()

        self.settings_page.set_locked_actions(self.ACTION_TO_LOCK)
        self.settings_page.save_and_wait_for_toaster()

        self.settings_page.refresh()
        self.settings_page.switch_to_page()

        self.settings_page.click_feature_flags()
        wait_until(lambda: self.settings_page.is_locked_action(self.ACTION_TO_LOCK))

        self.settings_page.set_locked_actions(self.ACTION_TO_LOCK)
        self.settings_page.save_and_wait_for_toaster()

    def test_feature_flags_regular_user(self):
        self.settings_page.switch_to_page()
        with pytest.raises(NoSuchElementException):
            self.settings_page.click_feature_flags()

    def test_locked_actions(self):
        db_locked_actions = self.axonius_system.db.gui_config_collection().find_one({
            'config_name': FEATURE_FLAGS_CONFIG
        })['config']['locked_actions']
        self.enforcements_page.switch_to_page()
        self.enforcements_page.click_new_enforcement()

        for action_name in db_locked_actions:
            action_title = Action[action_name].value
            self.enforcements_page.fill_action_library_search(action_title)
            self.enforcements_page.open_first_action_category()
            self.enforcements_page.click_action(action_title)
            assert self.enforcements_page.find_action_library_tip('Please reach out to your Account Manager')
            self.enforcements_page.click_ok_button()
            self.enforcements_page.wait_for_modal_close()
            self.enforcements_page.open_first_action_category()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        ui_locked_actions = self.settings_page.get_locked_actions().split(', ')

        assert len(ui_locked_actions) == len(db_locked_actions)
        for action_name in db_locked_actions:
            assert Action[action_name].value in ui_locked_actions
        self.settings_page.set_locked_actions(self.ACTION_TO_LOCK)
        self.settings_page.set_locked_actions(self.ACTION_TO_UNLOCK)
        self.settings_page.save_and_wait_for_toaster()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=self.password)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.open_action_category(ActionCategory.Incident)
        self.enforcements_page.click_action(self.ACTION_TO_LOCK)
        assert self.enforcements_page.find_action_library_tip('Please reach out to your Account Manager')
        self.enforcements_page.click_ok_button()
        self.enforcements_page.wait_for_modal_close()

        self.enforcements_page.add_generic_action(ActionCategory.Isolate, self.ACTION_TO_UNLOCK, 'Unlocked Action')

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.set_locked_actions(self.ACTION_TO_LOCK)
        self.settings_page.set_locked_actions(self.ACTION_TO_UNLOCK)
        self.settings_page.save_and_wait_for_toaster()

    def _change_expiration_date(self, days_remaining=None, existing=True):
        try:
            self.login_page.find_disabled_login_button()
        except NoSuchElementException:
            # We are logged in - need to logout
            self.login_page.logout()

        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        if existing:
            self.settings_page.find_existing_date()
        self.settings_page.fill_trial_expiration_by_remainder(days_remaining)
        self.settings_page.save_and_wait_for_toaster()
        self.login_page.logout()
        time.sleep(6)
        self.login_page.refresh()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=self.password)

    def test_trial_expiration(self):
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_trial_remainder_banner(30)
        for days_remaining in [16, 8, 2]:
            self._change_expiration_date(days_remaining)
            assert self.dashboard_page.find_trial_remainder_banner(days_remaining)

        self._change_expiration_date()
        self.dashboard_page.find_no_trial_banner()

        self._change_expiration_date(-1, existing=False)
        assert self.dashboard_page.find_trial_expired_banner()
        self.restart_browser()
        self._change_expiration_date()
        self.dashboard_page.find_no_trial_banner()

        self._change_expiration_date(-1, existing=False)
        assert self.dashboard_page.find_trial_expired_banner()
        self.restart_browser()
        self._change_expiration_date(3)
        self.dashboard_page.find_no_trial_banner()
