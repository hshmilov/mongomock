import pytest

from selenium import webdriver

from services.ports import DOCKER_PORTS
from ui_tests.pages.login_page import LoginPage
from ui_tests.pages.settings_page import SettingsPage
from ui_tests.pages.devices_page import DevicesPage
from test_credentials.test_gui_credentials import DEFAULT_USER


class TestBase:
    def _initialize_driver(self):
        if pytest.config.option.local_browser:
            self.driver = webdriver.Chrome()
            self.base_url = 'https://127.0.0.1'
        else:
            self.driver = webdriver.Remote(command_executor=f'http://127.0.0.1:{DOCKER_PORTS["selenium-hub"]}/wd/hub',
                                           desired_capabilities=webdriver.DesiredCapabilities.CHROME)
            self.base_url = 'https://gui'

    def setup_method(self, method):
        self._initialize_driver()
        self.driver.maximize_window()
        self.driver.implicitly_wait(0.3)
        self.username = DEFAULT_USER['user_name']
        self.password = DEFAULT_USER['password']

        self.register_pages()
        self.log_in()

    def teardown_method(self, method):
        if self.driver:
            self.driver.quit()

    def register_pages(self):
        params = dict(driver=self.driver, base_url=self.base_url)
        self.login_page = LoginPage(**params)
        self.settings_page = SettingsPage(**params)
        self.devices_page = DevicesPage(**params)

    def log_in(self):
        self.driver.get(self.base_url)
        self.login_page.login(username=self.username, password=self.password)
