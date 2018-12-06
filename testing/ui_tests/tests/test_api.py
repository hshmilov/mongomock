from urllib import parse

import requests
from ui_tests.tests.ui_test_base import TestBase


def get_device_views_from_api(account_data):
    api_url = parse.urljoin('https://localhost', 'api/V1/')
    device_views_url = parse.urljoin(api_url, 'devices/views')

    params = {'limit': 1000, 'skip': 0, 'filter': 'query_type==\'saved\''}
    headers = {'api-key': account_data['key'], 'api-secret': account_data['secret']}

    return requests.get(device_views_url, params, headers=headers, verify=False)


class TestAxoniusAPI(TestBase):
    def test_api_auth_key(self):
        self.account_page.switch_to_page()
        self.account_page.wait_for_spinner_to_end()
        account_data = self.account_page.get_api_key_and_secret()
        assert get_device_views_from_api(account_data).status_code == 200

    def test_api_auth_key_revoke(self):
        self.account_page.switch_to_page()
        self.account_page.wait_for_spinner_to_end()
        account_data = self.account_page.get_api_key_and_secret()

        assert get_device_views_from_api(account_data).status_code == 200

        self.account_page.reset_api_key_and_secret()
        new_account_data = self.account_page.get_api_key_and_secret()

        assert new_account_data['key'] != account_data['key']
        assert new_account_data['secret'] != account_data['secret']
        assert get_device_views_from_api(account_data).status_code != 200
        assert get_device_views_from_api(new_account_data).status_code == 200
