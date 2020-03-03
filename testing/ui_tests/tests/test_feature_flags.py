import time

import pytest
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from services.adapters.cybereason_service import CybereasonService

from test_credentials.test_gui_credentials import AXONIUS_USER
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.pages.enforcements_page import Action, ActionCategory
from axonius.utils.wait import wait_until
from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG


class TestFeatureFlags(TestBase):

    ACTION_TO_LOCK = Action.carbonblack_defense_quarantine.value

    def test_feature_flags_axonius_user(self):
        self.devices_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()

        wait_until(lambda: self.settings_page.set_locked_actions(self.ACTION_TO_LOCK), check_return_value=False,
                   tolerated_exceptions_list=[NoSuchElementException, ElementNotInteractableException])
        self.settings_page.save_and_wait_for_toaster()

        self.settings_page.refresh()
        self.settings_page.switch_to_page()

        self.settings_page.click_feature_flags()
        wait_until(lambda: self.settings_page.is_locked_action(self.ACTION_TO_LOCK))

        wait_until(lambda: self.settings_page.set_locked_actions(self.ACTION_TO_LOCK), check_return_value=False,
                   tolerated_exceptions_list=[NoSuchElementException, ElementNotInteractableException])
        self.settings_page.save_and_wait_for_toaster()

    def test_feature_flags_regular_user(self):
        self.settings_page.switch_to_page()
        with pytest.raises(NoSuchElementException):
            self.settings_page.click_feature_flags()

    def _try_to_add_locked_action(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.add_generic_action(ActionCategory.Isolate, self.ACTION_TO_LOCK,
                                                  'Unlocked Action')

    def test_locked_actions(self):
        with CybereasonService().contextmanager(take_ownership=True):
            db_locked_actions = self.axonius_system.db.gui_config_collection().find_one({
                'config_name': FEATURE_FLAGS_CONFIG
            })['config']['locked_actions']
            assert not len(db_locked_actions)

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
            self.settings_page.switch_to_page()
            self.settings_page.click_feature_flags()
            ui_locked_actions = self.settings_page.get_multiple_select_values()

            assert len(ui_locked_actions) == len(db_locked_actions)
            for action_name in db_locked_actions:
                assert Action[action_name].value in ui_locked_actions
            self.settings_page.set_locked_actions(self.ACTION_TO_LOCK)
            self.settings_page.save_and_wait_for_toaster()

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=self.username, password=self.password)
            self.enforcements_page.switch_to_page()
            self.enforcements_page.click_new_enforcement()
            self.enforcements_page.open_action_category(ActionCategory.Isolate)
            self.enforcements_page.click_action(self.ACTION_TO_LOCK)
            assert self.enforcements_page.find_action_library_tip('Please reach out to your Account Manager')
            self.enforcements_page.click_ok_button()
            self.enforcements_page.wait_for_modal_close()

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
            self.settings_page.switch_to_page()
            self.settings_page.click_feature_flags()
            self.settings_page.set_locked_actions(self.ACTION_TO_LOCK)
            self.settings_page.save_and_wait_for_toaster()

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=self.username, password=self.password)
            self.enforcements_page.switch_to_page()
            self.enforcements_page.click_new_enforcement()
            wait_until(self._try_to_add_locked_action,
                       tolerated_exceptions_list=[NoSuchElementException], total_timeout=60 * 5,
                       check_return_value=False)

    def _change_expiration_date(self, days_remaining=None, existing=True, contract=False):
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
        if contract:
            self.settings_page.fill_contract_expiration_by_remainder(days_remaining)
        else:
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
        self.dashboard_page.find_no_trial_banner()
        self._change_expiration_date(3)

    def test_contract_expiration(self):
        self.dashboard_page.switch_to_page()
        for days_remaining in [60, 15, 2]:
            self._change_expiration_date(days_remaining, contract=True)
            assert self.dashboard_page.find_contract_remainder_banner(days_remaining)

        self._change_expiration_date(contract=True)
        self.dashboard_page.find_banner_no_contract()

        self._change_expiration_date(-1, existing=False, contract=True)
        assert self.dashboard_page.find_contract_expired_banner()
        self.restart_browser()
        self._change_expiration_date(contract=True)
        self.dashboard_page.find_banner_no_contract()

        self._change_expiration_date(-1, existing=False, contract=True)
        assert self.dashboard_page.find_contract_expired_banner()
        self.restart_browser()
        self.dashboard_page.find_banner_no_contract()
        self._change_expiration_date(3, contract=True)
