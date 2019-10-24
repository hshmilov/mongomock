import json
import logging
import logging.handlers
import os
import re
import sys
from datetime import datetime, timedelta

import pytest
from passlib.hash import bcrypt
from retrying import retry
from selenium import webdriver

import conftest
from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, FeatureFlagsNames, DASHBOARD_SPACE_TYPE_CUSTOM
from axonius.consts.plugin_consts import AXONIUS_USER_NAME, CORE_UNIQUE_NAME, PLUGIN_NAME
from axonius.consts.system_consts import AXONIUS_DNS_SUFFIX, LOGS_PATH_HOST
from axonius.plugin_base import EntityType
from axonius.utils.mongo_administration import truncate_capped_collection
from services.axonius_service import get_service
from services.ports import DOCKER_PORTS
from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.pages.account_page import AccountPage
from ui_tests.pages.adapters_page import AdaptersPage
from ui_tests.pages.base_page import BasePage
from ui_tests.pages.dashboard_page import DashboardPage
from ui_tests.pages.devices_page import DevicesPage
from ui_tests.pages.devices_queries_page import DevicesQueriesPage
from ui_tests.pages.enforcements_page import EnforcementsPage
from ui_tests.pages.instances_page import InstancesPage
from ui_tests.pages.login_page import LoginPage
from ui_tests.pages.my_account_page import MyAccountPage
from ui_tests.pages.notification_page import NotificationPage
from ui_tests.pages.reports_page import ReportsPage
from ui_tests.pages.settings_page import SettingsPage
from ui_tests.pages.signup_page import SignupPage
from ui_tests.pages.users_page import UsersPage
from ui_tests.tests.ui_consts import ROOT_DIR

SCREENSHOTS_FOLDER = os.path.join(ROOT_DIR, 'screenshots')
LOGS_FOLDER = os.path.join(LOGS_PATH_HOST, 'ui_logger')
DOCKER_NETWORK_DEFAULT_GATEWAY = '172.17.0.1'


def create_ui_tests_logger():
    if not os.path.exists(LOGS_FOLDER):
        os.makedirs(LOGS_FOLDER)
    file_path = os.path.join(LOGS_FOLDER, 'ui_tests.log')
    file_handler = logging.handlers.RotatingFileHandler(file_path,
                                                        maxBytes=5 * 1024 * 1024,
                                                        backupCount=3)
    my_logger = logging.getLogger('axonius')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(formatter)
    my_logger.addHandler(file_handler)
    my_logger.setLevel(logging.DEBUG)
    return my_logger


logger = create_ui_tests_logger()


# pylint: disable=too-many-instance-attributes
# pylint: disable=no-value-for-parameter


class TestBase:
    def _initialize_driver(self):
        if pytest.config.option.local_browser:
            self.local_browser = True
            self.driver = self._get_local_browser()
            self.base_url = 'https://127.0.0.1'
            self.port = 443
        elif pytest.config.option.host_hub:
            self.local_browser = False
            self.port = 443
            remote_hub = f'http://{os.environ["REMOTE_HUB_ADDR"]}:4444/wd/hub'
            self.base_url = f'https://{os.environ["LOCAL_EXTERNAL_ADDR"]}'
            logger.info(f'Base Url: {self.base_url}')
            logger.info(f'Connecting to the remote hub {remote_hub}..')
            self.driver = webdriver.Remote(
                command_executor=remote_hub,
                desired_capabilities=self._get_desired_capabilities())
            logger.info('Connected successfully!')
        else:
            self.local_browser = False
            self.port = 443
            logger.info('Before webdriver.Remote')
            self.driver = webdriver.Remote(command_executor=f'http://127.0.0.1:{DOCKER_PORTS["selenium-hub"]}/wd/hub',
                                           desired_capabilities=self._get_desired_capabilities())
            logger.info('After webdriver.Remote')
            self.base_url = f'https://gui.{AXONIUS_DNS_SUFFIX}'

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

    @staticmethod
    def _get_current_test_id():
        """
        Returns the current running test, formatted as a teamcity test id.
        The code is taken from teamcity-messages-1.21, pytest plguin, format_test_id method.
        :return:
        """
        test_id = os.environ['PYTEST_CURRENT_TEST'].split(' ')[0]
        if test_id:
            if test_id.find('::') < 0:
                test_id += '::top_level'
        else:
            test_id = 'top_level'

        first_bracket = test_id.find('[')
        if first_bracket > 0:
            # [] -> (), make it look like nose parameterized tests
            params = '(' + test_id[first_bracket + 1:]
            if params.endswith(']'):
                params = params[:-1] + ')'
            test_id = test_id[:first_bracket]
            if test_id.endswith('::'):
                test_id = test_id[:-2]
        else:
            params = ''

        test_id = test_id.replace('::()::', '::')
        test_id = re.sub(r'\.pyc?::', r'::', test_id)
        test_id = test_id.replace('.', '_').replace(os.sep, '.').replace('/', '.').replace('::', '.')

        if params:
            params = params.replace('.', '_')
            test_id += params

        return test_id

    def _save_screenshot(self, text=''):
        if not self.driver:
            return
        try:
            folder = os.path.join(SCREENSHOTS_FOLDER, self._get_current_test_id())
            if not os.path.exists(folder):
                os.makedirs(folder)
            current_time = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
            file_path = os.path.join(
                folder,
                f'_{self.driver.name}_{current_time}_{text}.png')
            self.driver.save_screenshot(file_path)
        except Exception:
            logger.exception('Error while saving screenshot')

    def _save_js_logs(self):
        if not self.driver:
            return
        try:
            # this is copied as-is from _save_screenshot so it will appear in the same directory
            folder = os.path.join(SCREENSHOTS_FOLDER, self._get_current_test_id())
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

    @retry(wait_fixed=100, stop_max_delay=60000)
    def _clean_db(self):
        if not self.axonius_system:
            return

        # Wait until scheduler finishes
        self.axonius_system.scheduler.wait_for_scheduler(True)
        # wait again, in case something is racy
        self.axonius_system.scheduler.wait_for_scheduler(True)

        self.axonius_system.get_devices_db().delete_many({})
        self.axonius_system.get_users_db().delete_many({})
        self.axonius_system.get_enforcements_db().delete_many({})
        self.axonius_system.get_actions_db().delete_many({})
        self.axonius_system.get_tasks_db().delete_many({})
        self.axonius_system.get_tasks_running_id_db().delete_many({})
        self.axonius_system.get_notifications_db().delete_many({})
        self.axonius_system.get_reports_config_db().delete_many({})
        self.axonius_system.get_dashboard_spaces_db().delete_many({
            'type': DASHBOARD_SPACE_TYPE_CUSTOM
        })
        self.axonius_system.get_dashboard_db().delete_many({
            'user_id': {
                '$ne': '*'
            }
        })

        truncate_capped_collection(self.axonius_system.db.get_historical_entity_db_view(EntityType.Users))
        truncate_capped_collection(self.axonius_system.db.get_historical_entity_db_view(EntityType.Devices))

        self.axonius_system.get_system_users_db().delete_many(
            {'user_name': {'$nin': [AXONIUS_USER_NAME, DEFAULT_USER['user_name']]}})
        self.axonius_system.get_system_users_db().update_one(
            {'user_name': DEFAULT_USER['user_name']}, {'$set': {'password': bcrypt.hash(DEFAULT_USER['password'])}})

        self.axonius_system.db.remove_gui_dynamic_fields(EntityType.Users)
        self.axonius_system.db.remove_gui_dynamic_fields(EntityType.Devices)

        self.axonius_system.db.restore_gui_entity_views(EntityType.Users)
        self.axonius_system.db.restore_gui_entity_views(EntityType.Devices)

        self.axonius_system.db.gui_config_collection().update_one({
            'config_name': FEATURE_FLAGS_CONFIG
        }, {
            '$set': {
                f'config.{FeatureFlagsNames.TrialEnd}':
                    (datetime.now() + timedelta(days=30)).isoformat()[:10].replace('-', '/')
            }
        })

    def change_base_url(self, new_url):
        old_base_url = self.base_url
        self.base_url = new_url
        self.driver.get(self.driver.current_url.replace(old_base_url, new_url))

    def setup_method(self, method):
        logger.info(f'starting setup_method {method.__name__}')
        self.logger = logger
        self.setup_browser()

        self.username = DEFAULT_USER['user_name']
        self.password = DEFAULT_USER['password']
        self.axonius_system = get_service()

        self.login()
        logger.info(f'finishing setup_method {method.__name__}')

    def setup_browser(self):
        self._initialize_driver()

        # mac issues, maximize is not working on mac anyway now
        if sys.platform != 'darwin':
            self.driver.maximize_window()

        self.driver.implicitly_wait(0.3)
        self.driver.set_page_load_timeout(30)
        self.driver.set_script_timeout(30)
        self.register_pages()

    def restart_browser(self):
        self.driver.quit()
        self.setup_browser()
        self.driver.get(self.base_url)

    def teardown_method(self, method):
        logger.info(f'starting teardown_method {method.__name__}')
        self._save_screenshot(text='before_teardown')
        self._save_js_logs()
        if not pytest.config.option.teardown_keep_db:
            self._clean_db()
        if self.driver:
            self.driver.quit()
        logger.info(f'finishing teardown_method {method.__name__}')

    def register_pages(self):
        params = dict(driver=self.driver, base_url=self.base_url, local_browser=self.local_browser, test_base=self)
        self.base_page = BasePage(**params)
        self.login_page = LoginPage(**params)
        self.settings_page = SettingsPage(**params)
        self.my_account_page = MyAccountPage(**params)
        self.devices_page = DevicesPage(**params)
        self.devices_queries_page = DevicesQueriesPage(**params)
        self.users_page = UsersPage(**params)
        self.reports_page = ReportsPage(**params)
        self.enforcements_page = EnforcementsPage(**params)
        self.adapters_page = AdaptersPage(**params)
        self.notification_page = NotificationPage(**params)
        self.dashboard_page = DashboardPage(**params)
        self.account_page = AccountPage(**params)
        self.instances_page = InstancesPage(**params)
        self.signup_page = SignupPage(**params)

    def get_all_screens(self):
        screens = (self.devices_page,
                   self.users_page,
                   self.enforcements_page,
                   self.adapters_page,
                   self.reports_page,
                   self.instances_page)
        return screens

    def should_getting_started_open(self):
        is_getting_started_enabled = self.axonius_system.db.core_settings_getting_started()
        is_getting_started_autoopen = self.axonius_system.db.gui_getting_started_auto()

        return is_getting_started_enabled and is_getting_started_autoopen

    # wait for the element and

    def login(self):
        self.driver.get(self.base_url)
        self.fill_signup_screen()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=self.password, remember_me=True)

    def fill_signup_screen(self):
        if self.axonius_system.gui.get_signup_status() is False:
            self.signup_page.wait_for_signup_page_to_load()
            self.signup_page.fill_signup_with_defaults_and_save()

    def _create_history(self, entity_type: EntityType, update_field=None, days_to_fill=30):
        history_db = self.axonius_system.db.get_historical_entity_db_view(entity_type)
        entity_count = self.axonius_system.db.get_entity_db(entity_type).count_documents({})
        if not entity_count:
            self.base_page.run_discovery()
            return []
        day_to_entity_count = []
        for day in range(1, days_to_fill):
            # Randomly select a chunk of entities to be added as history for `day` back
            entity_limit = entity_count
            entities = list(history_db.find(limit=entity_limit))
            current_date = datetime.now() - timedelta(day)
            for entity in entities:
                del entity['_id']
                # Update the historical date being generated
                entity['accurate_for_datetime'] = current_date
                if update_field:
                    entity['adapters'][0]['data'][update_field] += f' {day}'

            insert_many_result = history_db.insert_many(entities)
            # Save the count for testing the expected amount for the day is presented
            day_to_entity_count.append(len(insert_many_result.inserted_ids))
        self.base_page.run_discovery()
        return day_to_entity_count

    def _update_and_create_history(self, entity_type: EntityType):
        self.axonius_system.db.get_historical_entity_db_view(entity_type).drop()
        self.base_page.run_discovery()
        self._create_history(entity_type)
        self.base_page.refresh()

    @retry(stop_max_attempt_number=150, wait_fixed=3000)
    def wait_for_adapter_down(self, adapter_name):
        # Adapters will go down by themselves when there are no clients
        # This is effectively testing AOD
        assert self.axonius_system.db.get_collection(CORE_UNIQUE_NAME, 'configs').find_one({
            PLUGIN_NAME: adapter_name
        })['status'] == 'down'
