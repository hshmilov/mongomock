import os

from ui_tests.tests.ui_consts import LOGS_AFTER_UPGRADE_PATH
from ui_tests.tests.ui_test_base import TestBase


class TestPerCustomerSettings(TestBase):
    # pylint: disable=no-self-use
    def test_add_nimbul(self):
        # Testing that nimbul was up and generated logs.
        # Because the AOD stops it.
        assert any('nimbul' in current_dir for current_dir in os.listdir(LOGS_AFTER_UPGRADE_PATH))
