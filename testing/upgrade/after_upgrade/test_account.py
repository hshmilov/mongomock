import json
from pathlib import Path

from ui_tests.tests.ui_consts import Account
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.test_api import get_device_views_from_api


class TestPrepareAlert(TestBase):
    def test_api_key(self):
        self.account_page.switch_to_page()
        self.account_page.wait_for_spinner_to_end()
        account_data = self.account_page.get_api_key_and_secret()
        stored = json.loads(Path(Account.file_path).read_text())
        assert stored == account_data
        assert get_device_views_from_api(account_data).status_code == 200
