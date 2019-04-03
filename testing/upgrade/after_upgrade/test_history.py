from datetime import datetime, timedelta

from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import History


def _check_history_of_entity(page: EntitiesPage):
    page.switch_to_page()
    page.wait_for_table_to_load()
    for day in range(1, History.history_depth + 1):
        page.fill_datepicker_date(datetime.now() - timedelta(day))
        page.wait_for_table_to_load()
        assert page.count_entities() >= History.entities_per_day
        page.close_datepicker()
        page.clear_existing_date()


class TestHistory(TestBase):
    def test_history(self):
        _check_history_of_entity(self.devices_page)
        _check_history_of_entity(self.users_page)
