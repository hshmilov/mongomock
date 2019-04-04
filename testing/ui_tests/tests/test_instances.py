import time

import requests

from CI.scripts.axonius_builds_context.axoniusbuilds import builds
from ui_tests.tests.ui_test_base import TestBase

NODE_MAKER_USERNAME = 'node_maker'
NODE_MAKER_PASSWORD = 'M@ke1tRain'

DEFAULT_LIMIT = 10

EXPORTS_ENDPOINT = 'exports'
DAILY_EXPORT_SUFFIX = '_daily_export'
DAILY_EXPORT_DATE_FORMAT = '%Y%m%d'


def get_latest_export():
    response = requests.get(url=f'{builds.BUILDS_SERVER_URL}/{EXPORTS_ENDPOINT}', params={'limit': DEFAULT_LIMIT},
                            verify=False)
    data = response.json()
    daily_exports = [export for export in data['result'] if DAILY_EXPORT_SUFFIX in export['version']]
    latest_daily_export = daily_exports[0]

    return latest_daily_export


def setup_instances(logger):
    latest_export = get_latest_export()
    logger.info(f'using {latest_export["version"]} for instances tests')
    instances = {
        'node_1': builds.Instance('test_node_1', ami=latest_export['ami_id']),
    }

    for current_instance in instances.values():
        current_instance.init_server()
        current_instance.connect_ssh(password=current_instance.sshpass)
        current_instance.wait_for_booted_for_production()

    return instances


class TestInstances(TestBase):
    def setup_method(self, method):
        super().setup_method(method)
        self._instances = setup_instances(self.logger)

    def teardown_method(self, method):
        for current_instance in self._instances.values():
            current_instance.terminate()

        super().teardown_method(method)

    def test_nodemaker_user_exists(self):
        self._instances['node_1'].connect_ssh(username=NODE_MAKER_USERNAME, password=NODE_MAKER_PASSWORD)

    def test_nodemaker_user_delete_after_login(self):
        assert NODE_MAKER_USERNAME in self._instances['node_1'].ssh('cat /etc/passwd')[0]
        self.change_base_url(f'https://{self._instances["node_1"].ip}')
        self.signup_page.wait_for_signup_page_to_load()
        self.signup_page.fill_signup_with_defaults_and_save()
        self.login_page.wait_for_login_page_to_load()
        self.login()
        time.sleep(61)
        assert NODE_MAKER_USERNAME not in self._instances['node_1'].ssh('cat /etc/passwd')[0]
