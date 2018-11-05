import json
import logging
import os
from datetime import datetime

import pytest
from selenium import webdriver

import conftest
from axonius.consts.plugin_consts import AXONIUS_USER_NAME
from axonius.plugin_base import EntityType
from services.axonius_service import get_service
from services.ports import DOCKER_PORTS
from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.pages.adapters_page import AdaptersPage
from ui_tests.pages.alert_page import AlertPage
from ui_tests.pages.base_page import BasePage
from ui_tests.pages.devices_page import DevicesPage
from ui_tests.pages.devices_queries_page import DevicesQueriesPage
from ui_tests.pages.login_page import LoginPage
from ui_tests.pages.my_account_page import MyAccountPage
from ui_tests.pages.notification_page import NotificationPage
from ui_tests.pages.report_page import ReportPage
from ui_tests.pages.settings_page import SettingsPage
from ui_tests.pages.users_page import UsersPage

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=too-many-instance-attributes


class TestBase:
    def _initialize_driver(self):
        if pytest.config.option.local_browser:
            self.driver = self._get_local_browser()
            self.base_url = 'https://127.0.0.1'
        else:
            self.driver = webdriver.Remote(command_executor=f'http://127.0.0.1:{DOCKER_PORTS["selenium-hub"]}/wd/hub',
                                           desired_capabilities=self._get_desired_capabilities())
            self.base_url = 'https://gui'

    @staticmethod
    def _get_desired_capabilities():
        if pytest.config.option.browser == conftest.CHROME:
            return webdriver.DesiredCapabilities.CHROME
        if pytest.config.option.browser == conftest.FIREFOX:
            ff_profile = webdriver.FirefoxProfile()
            ff_profile.set_preference('security.insecure_field_warning.contextual.enabled', False)
            ff_profile.set_preference('security.insecure_password.ui.enabled', False)
            ff_opts = webdriver.firefox.options.Options()
            ff_opts.profile = ff_profile
            ff_caps = ff_opts.to_capabilities()
            ff_caps.update(webdriver.DesiredCapabilities.FIREFOX)
            return ff_caps
        raise AssertionError('Invalid browser selected')

    @staticmethod
    def _get_local_browser():
        if pytest.config.option.browser == conftest.CHROME:
            return webdriver.Chrome()
        if pytest.config.option.browser == conftest.FIREFOX:
            return webdriver.Firefox()
        raise AssertionError('Invalid browser selected')

    def _save_screenshot(self, method, text=''):
        if not self.driver:
            return
        try:
            folder = os.path.join('screenshots', method.__name__)
            if not os.path.exists(folder):
                os.makedirs(folder)
            current_time = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
            file_path = os.path.join(
                folder,
                f'_{self.driver.name}_{current_time}_{text}.png')
            self.driver.save_screenshot(file_path)
        except Exception:
            logger.exception('Error while saving screenshot')

    def _save_js_logs(self, method):
        if not self.driver:
            return
        try:
            # this is copied as-is from _save_screenshot so it will appear in the same directory
            folder = os.path.join('screenshots', method.__name__)
            if not os.path.exists(folder):
                os.makedirs(folder)
            current_time = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
            for log_type in self.driver.log_types:
                file_path = os.path.join(
                    folder,
                    f'_{self.driver.name}_{current_time}_{log_type}.log')
                logs = self.driver.get_log(log_type)
                for log in logs:
                    timestamp = log.get('timestamp')
                    if timestamp:
                        log['date'] = str(datetime.fromtimestamp(timestamp / 1000))
                with open(file_path, 'w') as file:
                    file.writelines(json.dumps(x) for x in logs)

        except Exception:
            logger.exception('Error while saving JS logs')

    def _clean_db(self):
        if not self.axonius_system:
            return
        self.axonius_system.get_devices_db().remove()
        self.axonius_system.get_users_db().remove()
        self.axonius_system.get_reports_db().remove()
        self.axonius_system.get_notifications_db().remove()
        self.axonius_system.db.get_entity_db_view(EntityType.Users).remove()
        self.axonius_system.db.get_entity_db_view(EntityType.Devices).remove()
        self.axonius_system.get_system_users_db().remove({'user_name': {'$nin': [AXONIUS_USER_NAME, 'admin']}})

    def change_base_url(self, new_url):
        old_base_url = self.base_url
        self.base_url = new_url
        self.driver.get(self.driver.current_url.replace(old_base_url, new_url))

    def setup_method(self, method):
        self._initialize_driver()
        self.driver.maximize_window()
        self.driver.implicitly_wait(0.3)
        self.username = DEFAULT_USER['user_name']
        self.password = DEFAULT_USER['password']
        self.axonius_system = get_service()

        self.register_pages()
        self.login()

    def teardown_method(self, method):
        self._save_screenshot(method, text='before_teardown')
        self._save_js_logs(method)
        if not pytest.config.option.teardown_keep_db:
            self._clean_db()
        if self.driver:
            self.driver.quit()

    def register_pages(self):
        params = dict(driver=self.driver, base_url=self.base_url)
        self.base_page = BasePage(**params)
        self.login_page = LoginPage(**params)
        self.settings_page = SettingsPage(**params)
        self.my_account_page = MyAccountPage(**params)
        self.devices_page = DevicesPage(**params)
        self.devices_queries_page = DevicesQueriesPage(**params)
        self.users_page = UsersPage(**params)
        self.report_page = ReportPage(**params)
        self.alert_page = AlertPage(**params)
        self.adapters_page = AdaptersPage(**params)
        self.notification_page = NotificationPage(**params)

    def get_all_screens(self):
        screens = (self.devices_page,
                   self.users_page,
                   self.alert_page,
                   self.adapters_page,
                   self.report_page)
        return screens

    def login(self):
        self.driver.get(self.base_url)
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=self.password, remember_me=True)
