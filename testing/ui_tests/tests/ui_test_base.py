import logging
import os
from datetime import datetime

import pytest
from selenium import webdriver

from axonius.plugin_base import EntityType
from services.ports import DOCKER_PORTS
from services.axonius_service import get_service
from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.pages.base_page import BasePage
from ui_tests.pages.devices_page import DevicesPage
from ui_tests.pages.login_page import LoginPage
from ui_tests.pages.settings_page import SettingsPage
from ui_tests.pages.users_page import UsersPage
from ui_tests.pages.report_page import ReportPage
from ui_tests.pages.alert_page import AlertPage
from ui_tests.pages.notification_page import NotificationPage

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=too-many-instance-attributes


class TestBase:
    def _initialize_driver(self):
        if pytest.config.option.local_browser:
            self.driver = webdriver.Chrome()
            self.base_url = 'https://127.0.0.1'
        else:
            self.driver = webdriver.Remote(command_executor=f'http://127.0.0.1:{DOCKER_PORTS["selenium-hub"]}/wd/hub',
                                           desired_capabilities=webdriver.DesiredCapabilities.CHROME)
            self.base_url = 'https://gui'

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

    def _clean_db(self):
        if not self.axonius_system:
            return
        self.axonius_system.get_devices_db().remove()
        self.axonius_system.get_users_db().remove()
        self.axonius_system.db.get_entity_db_view(EntityType.Users).remove()
        self.axonius_system.db.get_entity_db_view(EntityType.Devices).remove()

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
        if not pytest.config.option.teardown_keep_db:
            self._clean_db()
        if self.driver:
            self.driver.quit()

    def register_pages(self):
        params = dict(driver=self.driver, base_url=self.base_url)
        self.base_page = BasePage(**params)
        self.login_page = LoginPage(**params)
        self.settings_page = SettingsPage(**params)
        self.devices_page = DevicesPage(**params)
        self.users_page = UsersPage(**params)
        self.report_page = ReportPage(**params)
        self.alert_page = AlertPage(**params)
        self.notification_page = NotificationPage(**params)

    def login(self):
        self.driver.get(self.base_url)
        self.login_page.login(username=self.username, password=self.password)
