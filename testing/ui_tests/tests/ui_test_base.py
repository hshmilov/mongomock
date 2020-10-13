import base64
import json
import logging
import logging.handlers
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta

import pytest
from passlib.hash import bcrypt
from retrying import retry
from selenium import webdriver
import selenium.common.exceptions
from selenium.webdriver.support.wait import WebDriverWait

from devops.scripts.backup.axonius_full_backup_restore import backup
import conftest

from axonius.saas.input_params import read_saas_input_params
from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG, FeatureFlagsNames, \
    DASHBOARD_SPACE_TYPE_CUSTOM, GUI_CONFIG_NAME, IDENTITY_PROVIDERS_CONFIG
from axonius.consts.plugin_consts import (AXONIUS_USERS_LIST, CORE_UNIQUE_NAME,
                                          PLUGIN_NAME, AGGREGATOR_PLUGIN_NAME,
                                          PASSWORD_SETTINGS, SYSTEM_COLUMNS_TYPE)
from axonius.consts.system_consts import AXONIUS_DNS_SUFFIX, LOGS_PATH_HOST
from axonius.plugin_base import EntityType
from axonius.utils.mongo_administration import truncate_capped_collection
from services.axonius_service import get_service
from services.ports import DOCKER_PORTS
from test_credentials.test_gui_credentials import DEFAULT_USER, AXONIUS_AWS_TESTS_USER
from ui_tests.pages.account_page import AccountPage
from ui_tests.pages.adapters_page import AdaptersPage
from ui_tests.pages.administration_page import AdministrationPage
from ui_tests.pages.audit_page import AuditPage
from ui_tests.pages.base_page import BasePage
from ui_tests.pages.compliance_page import CompliancePage
from ui_tests.pages.dashboard_page import DashboardPage
from ui_tests.pages.devices_page import DevicesPage
from ui_tests.pages.devices_queries_page import DevicesQueriesPage
from ui_tests.pages.reset_password_page import ResetPasswordPage
from ui_tests.pages.users_queries_page import UsersQueriesPage
from ui_tests.pages.enforcements_page import EnforcementsPage
from ui_tests.pages.instances_page import InstancesPage
from ui_tests.pages.login_page import LoginPage
from ui_tests.pages.notification_page import NotificationPage
from ui_tests.pages.reports_page import ReportsPage
from ui_tests.pages.settings_page import SettingsPage
from ui_tests.pages.signup_page import SignupPage
from ui_tests.pages.users_page import UsersPage
from ui_tests.tests.ui_consts import ROOT_DIR
from ui_tests.components.tag_component import TagComponent
from testing.tests.conftest import axonius_set_test_passwords

SCREENSHOTS_FOLDER = os.path.join(ROOT_DIR, 'screenshots')
LOGS_FOLDER = os.path.join(LOGS_PATH_HOST, 'ui_logger')
BACKUPS_FOLDER = os.path.join(ROOT_DIR, 'backups')
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


# pylint: disable=too-many-instance-attributes,no-value-for-parameter,no-member,access-member-before-definition,protected-access


class TestBase:
    def _initialize_driver(self, incognito_mode=False):
        self.ui_tests_download_dir = tempfile.TemporaryDirectory()
        if pytest.config.option.local_browser:
            self.local_browser = True
            self.driver = self._get_local_browser(self.ui_tests_download_dir.name, incognito_mode=incognito_mode)
            self.base_url = 'https://127.0.0.1'
            self.port = 443
        elif pytest.config.option.host_hub:
            self.local_browser = False
            self.port = 443
            remote_hub = f'http://{os.environ["REMOTE_HUB_ADDR"]}:4444/wd/hub'
            self.base_url = f'https://{os.environ["LOCAL_EXTERNAL_ADDR"]}'
            logger.info(f'Base Url: {self.base_url}')
            logger.info(f'Connecting to the remote hub {remote_hub}..')
            os.environ['XDG_DOWNLOAD_DIR'] = self.ui_tests_download_dir.name
            os.system('xdg-user-dirs-update --set DOWNLOAD ' + self.ui_tests_download_dir.name)
            options = webdriver.ChromeOptions()
            if incognito_mode:
                logger.info('Adding incognito mode')
                options.add_argument('--incognito')
            self.driver = webdriver.Remote(
                command_executor=remote_hub,
                options=options,
                desired_capabilities=self._get_desired_capabilities(incognito_mode=incognito_mode))
            logger.info('Connected successfully!')
        else:
            self.local_browser = False
            self.port = 443

            def should_retry(exception):
                logger.info(f'webdriver.Remote failed with exception {exception}')
                return isinstance(exception, selenium.common.exceptions.WebDriverException)

            @retry(retry_on_exception=should_retry, stop_max_attempt_number=3, wait_fixed=1000)
            def create_remote_driver():
                remote_options = webdriver.ChromeOptions()
                remote_port = DOCKER_PORTS['selenium-hub']
                if incognito_mode:
                    remote_options.add_argument('--incognito')
                return webdriver.Remote(command_executor=f'http://127.0.0.1:{remote_port}/wd/hub',
                                        options=remote_options,
                                        desired_capabilities=self._get_desired_capabilities(
                                            incognito_mode=incognito_mode)
                                        )

            logger.info('Before webdriver.Remote')
            if incognito_mode:
                logger.info('webdriver.Remote with incognito mode')
            self.driver = create_remote_driver()
            logger.info('After webdriver.Remote')
            self.base_url = f'https://gui.{AXONIUS_DNS_SUFFIX}'

    @staticmethod
    def _get_desired_capabilities(incognito_mode=False):
        if pytest.config.option.browser == conftest.CHROME:
            d = webdriver.DesiredCapabilities.CHROME
            d['goog:loggingPrefs'] = {'browser': 'ALL'}
            return d
        if pytest.config.option.browser == conftest.FIREFOX:
            ff_profile = webdriver.FirefoxProfile()
            ff_profile.set_preference('security.insecure_field_warning.contextual.enabled', False)
            ff_profile.set_preference('security.insecure_password.ui.enabled', False)
            ff_opts = webdriver.firefox.options.Options()
            ff_opts.profile = ff_profile
            ff_caps = ff_opts.to_capabilities()
            if incognito_mode:
                ff_caps.add_argument('-private')
            ff_caps.update(webdriver.DesiredCapabilities.FIREFOX)
            return ff_caps
        raise AssertionError('Invalid browser selected')

    @staticmethod
    def _get_local_browser(ui_tests_download_dir, incognito_mode=False):
        if pytest.config.option.browser == conftest.CHROME:
            options = webdriver.ChromeOptions()
            prefs = {'download.default_directory': ui_tests_download_dir}
            options.add_experimental_option('prefs', prefs)
            ext_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'Vue.js-devtools_v5.3.3.crx')
            options.add_extension(ext_path)
            options.add_argument('--ignore-certificate-errors')
            if incognito_mode:
                options.add_argument('--incognito')
            return webdriver.Chrome(chrome_options=options)
        if pytest.config.option.browser == conftest.FIREFOX:
            ff_opts = webdriver.firefox.options.Options()
            ff_caps = ff_opts.to_capabilities()
            if incognito_mode:
                ff_caps.add_argument('-private')
            return webdriver.Firefox(desired_capabilities=ff_caps)
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

    @staticmethod
    def save_backup(test_id, text=''):
        """
        Save database backup and some other axonius settings files using axonius_full_backup_restore
        :param test_id: test id from teamcity
        :param text: concat a text to the output filename
        :return:
        """
        try:
            folder = os.path.join(BACKUPS_FOLDER, test_id)
            if not os.path.exists(folder):
                os.makedirs(folder)
            current_time = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
            file_path = os.path.join(
                folder,
                f'_database_{current_time}_{text}.zip')
            backup(file_path)
        except Exception:
            logger.exception('Error while saving backup')

    def _save_js_logs(self):
        if not self.driver:
            return
        try:
            # this is copied as-is from _save_screenshot so it will appear in the same directory
            folder = os.path.join(SCREENSHOTS_FOLDER, self._get_current_test_id())
            if not os.path.exists(folder):
                os.makedirs(folder)
            current_time = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
            for log_type in self.driver.log_types + ['browser']:
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
        self.axonius_system.get_aggregator_devices_fields_db().delete_many({
            'name': {
                '$ne': 'hyperlinks'
            }
        })
        self.axonius_system.get_users_db().delete_many({})
        self.axonius_system.get_roles_db().delete_many({'predefined': {'$exists': False}})
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

        panels_ids = [str(id) for id in self.axonius_system.get_dashboard_db().find().distinct('_id')]
        self.axonius_system.get_dashboard_spaces_db().update_one(
            {'name': 'Axonius Dashboard'}, {'$set': {'panels_order': panels_ids}})
        self.axonius_system.get_dashboard_spaces_db().update_one(
            {'name': 'My Dashboard'}, {'$set': {'panels_order': []}})

        for name in self.axonius_system.db.client[AGGREGATOR_PLUGIN_NAME].list_collection_names():
            if not name.startswith('historical') or name.endswith('view'):
                continue
            self.axonius_system.db.client[AGGREGATOR_PLUGIN_NAME].drop_collection(name)

        truncate_capped_collection(self.axonius_system.db.get_historical_entity_db_view(EntityType.Users))
        truncate_capped_collection(self.axonius_system.db.get_historical_entity_db_view(EntityType.Devices))

        self.axonius_system.get_system_users_db().delete_many(
            {'user_name': {'$nin': AXONIUS_USERS_LIST + [DEFAULT_USER['user_name']]}})
        self.axonius_system.get_users_preferences_db().delete_many({})
        self.axonius_system.get_system_users_db().update_one(
            {'user_name': DEFAULT_USER['user_name']}, {'$set': {'password': bcrypt.hash(DEFAULT_USER['password'])}})

        self.axonius_system.db.remove_gui_dynamic_fields(EntityType.Users)
        self.axonius_system.db.remove_gui_dynamic_fields(EntityType.Devices)

        self.axonius_system.db.restore_gui_entity_views(EntityType.Users)
        self.axonius_system.db.restore_gui_entity_views(EntityType.Devices)

        self.axonius_system.db.plugins.gui.configurable_configs.update_config(
            FEATURE_FLAGS_CONFIG,
            {
                FeatureFlagsNames.TrialEnd: (datetime.now() + timedelta(days=30)).isoformat()[:10].replace('-', '/')
            }
        )

        self.axonius_system.db.plugins.core.configurable_configs.update_config(
            CORE_CONFIG_NAME,
            {
                f'{PASSWORD_SETTINGS}.enabled': False
            }
        )

        self.axonius_system.db.plugins.gui.configurable_configs.delete_config(GUI_CONFIG_NAME)
        self.axonius_system.db.plugins.gui.configurable_configs.delete_config(IDENTITY_PROVIDERS_CONFIG)
        self.axonius_system.gui.update_config()
        self.axonius_system.get_system_config_db().delete_one({'type': SYSTEM_COLUMNS_TYPE})
        self.axonius_system.get_aws_rules_db().update_many({}, {'$unset': {'comments': 1}})

    def change_base_url(self, new_url):
        old_base_url = self.base_url
        self.base_url = new_url
        self.driver.get(self.driver.current_url.replace(old_base_url, new_url))

    def setup_method(self, method):
        logger.info(f'starting setup_method {method.__name__}')
        self.setup_browser()
        self.init_system()
        logger.info(f'finishing setup_method {method.__name__}')

    @property
    def should_revert_passwords(self):
        return True

    def init_system(self):
        self.axonius_system = get_service()
        if self.should_revert_passwords:
            axonius_set_test_passwords()

        self.username = DEFAULT_USER['user_name'] if not read_saas_input_params() else \
            AXONIUS_AWS_TESTS_USER['user_name']
        self.password = DEFAULT_USER['password'] if not read_saas_input_params() else AXONIUS_AWS_TESTS_USER['password']

        self.login()
        self.base_page.wait_for_run_research()

    def setup_browser(self, incognito_mode=False):
        self.logger = logger
        self._initialize_driver(incognito_mode=incognito_mode)

        # mac issues, maximize is not working on mac anyway now
        if sys.platform != 'darwin':
            self.driver.maximize_window()

        self.driver.implicitly_wait(0.3)
        self.driver.set_page_load_timeout(30)
        self.driver.set_script_timeout(30)
        self.register_components()
        self.register_pages()

    def open_another_session(self, incognito_mode=False):
        new_test_base = TestBase()
        new_test_base.setup_browser(incognito_mode=incognito_mode)
        new_test_base.axonius_system = self.axonius_system
        new_test_base.driver.get(new_test_base.base_url)
        new_test_base.login_page.wait_for_login_page_to_load()
        return new_test_base

    def restart_browser(self):
        self.driver.quit()
        self.setup_browser()
        self.driver.get(self.base_url)

    def teardown_method(self, method):
        logger.info(f'starting teardown_method {method.__name__}')

        devices = self.axonius_system.db.get_entity_db(EntityType.Devices).count_documents({})
        users = self.axonius_system.db.get_entity_db(EntityType.Users).count_documents({})
        logger.info(f'number of devices: {devices}')
        logger.info(f'number of users: {users}')

        self._save_screenshot(text='before_teardown')
        self._save_js_logs()
        if not pytest.config.option.teardown_keep_db:
            self._clean_db()
        self.quit_browser()
        logger.info(f'finishing teardown_method {method.__name__}')

    def quit_browser(self):
        if self.driver:
            self.driver.quit()
        if self.ui_tests_download_dir:
            self.ui_tests_download_dir.cleanup()

    def register_pages(self):
        params = dict(driver=self.driver,
                      base_url=self.base_url,
                      local_browser=self.local_browser,
                      test_base=self)
        self.base_page = BasePage(**params)
        self.login_page = LoginPage(**params)
        self.reset_password_page = ResetPasswordPage(**params)
        self.settings_page = SettingsPage(**params)
        self.devices_page = DevicesPage(**params)
        self.devices_queries_page = DevicesQueriesPage(**params)
        self.users_queries_page = UsersQueriesPage(**params)
        self.users_page = UsersPage(**params)
        self.reports_page = ReportsPage(**params)
        self.enforcements_page = EnforcementsPage(**params)
        self.adapters_page = AdaptersPage(**params)
        self.notification_page = NotificationPage(**params)
        self.dashboard_page = DashboardPage(**params)
        self.account_page = AccountPage(**params)
        self.instances_page = InstancesPage(**params)
        self.signup_page = SignupPage(**params)
        self.compliance_page = CompliancePage(**params)
        self.administration_page = AdministrationPage(**params)
        self.audit_page = AuditPage(**params)

    def register_components(self):
        params = dict(driver=self.driver,
                      base_url=self.base_url,
                      local_browser=self.local_browser,
                      test_base=self)
        self.tag_component = TagComponent(**params)

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

    def login(self, remember_me=True, wait_for_getting_started=True):
        self.driver.get(self.base_url)
        self.fill_signup_screen()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=self.password, remember_me=remember_me,
                              wait_for_getting_started=wait_for_getting_started)

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
        for day in range(1, days_to_fill + 1):
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
        self.base_page.hard_refresh()
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

    def wait_for_stress_adapter_down(self, adapter_name):
        return self
        # try:
        #     self.wait_for_adapter_down(adapter_name)
        # except AssertionError:
        #     pass
        # self.wait_for_adapter_down(adapter_name)

    def get_current_window(self):
        return self.driver.current_window_handle

    def open_new_tab(self):
        self.driver.execute_script(f'window.open("{self.base_url}");')
        return self.driver.window_handles[len(self.driver.window_handles) - 1]

    def open_empty_tab(self):
        self.driver.execute_script(f'window.open("");')
        return self.driver.window_handles[len(self.driver.window_handles) - 1]

    def close_tab(self):
        self.driver.execute_script(f'window.close();')

    def switch_tab(self, tab):
        self.driver.switch_to.window(tab)

    def get_downloaded_file_content(self, file_name_substring, file_suffix):
        def correct_file_name(name):
            return name.endswith(file_suffix) and file_name_substring in name
        if pytest.config.option.local_browser:
            for root, dirs, files in os.walk(self.ui_tests_download_dir.name):
                for file_name in files:
                    if correct_file_name(file_name):
                        with open(f'{self.ui_tests_download_dir.name}/{file_name}', 'rb') as f:
                            return f.read()
        else:
            content = None
            current_tab = self.get_current_window()
            empty_tab = self.open_empty_tab()
            self.switch_tab(empty_tab)
            files = WebDriverWait(self.driver, 20, 1).until(self.get_downloaded_files)
            for file_name in files:
                if correct_file_name(file_name):
                    content = self.get_file_content(file_name)
            self.close_tab()
            self.switch_tab(current_tab)
            return content
        return None

    @staticmethod
    def get_downloaded_files(driver):
        if not driver.current_url.startswith('chrome://downloads'):
            driver.get('chrome://downloads/')

        return driver.execute_script(
            'return downloads.Manager.get().items_   '
            '  .filter(e => e.state === "COMPLETE")  '
            '  .map(e => e.filePath || e.file_path); ')

    def get_file_content(self, path):
        if not self.driver.current_url.startswith('chrome://downloads'):
            self.driver.get('chrome://downloads/')
        elem = self.driver.execute_script(
            'var input = window.document.createElement("INPUT"); '
            'input.setAttribute("type", "file"); '
            'input.hidden = true; '
            'input.onchange = function (e) { e.stopPropagation() }; '
            'return window.document.documentElement.appendChild(input); ')

        elem._execute('sendKeysToElement', {'value': [path], 'text': path})

        result = self.driver.execute_async_script(
            'var input = arguments[0], callback = arguments[1]; '
            'var reader = new FileReader(); '
            'reader.onload = function (ev) { callback(reader.result) }; '
            'reader.onerror = function (ex) { callback(ex.message) }; '
            'reader.readAsDataURL(input.files[0]); '
            'input.remove(); ', elem)

        if not result.startswith('data:'):
            raise Exception('Failed to get file content: %s' % result)

        return base64.b64decode(result[result.find('base64,') + 7:])
