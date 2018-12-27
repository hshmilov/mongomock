from services.adapters.nimbul_service import NimbulService
from ui_tests.tests.ui_test_base import TestBase


class TestPerCustomerSettings(TestBase):
    # pylint: disable=no-self-use
    def test_add_nimbul(self):
        ns = NimbulService()
        assert ns.is_up()
