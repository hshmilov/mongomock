import time
import json
from pathlib import Path

from ui_tests.tests.ui_consts import Account
from ui_tests.tests.ui_test_base import TestBase


class TestPrepareAlert(TestBase):
    def test_api_key(self):
        # since this is the first test, sometimes we are doing stuff before it was actually loaded
        time.sleep(5)
        self.account_page.switch_to_page()
        self.account_page.wait_for_spinner_to_end()
        account_data = self.account_page.get_api_key_and_secret()
        Path(Account.file_path).write_text(json.dumps(account_data))
