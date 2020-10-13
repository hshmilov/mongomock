from ui_tests.tests.ui_test_base import TestBase


class UpgradeTestBase(TestBase):
    @property
    def should_revert_passwords(self):
        return False
