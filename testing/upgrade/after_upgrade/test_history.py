from datetime import datetime, timedelta

from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import History


def _check_history_of_entity(page: EntitiesPage):
    page.switch_to_page()
    page.wait_for_table_to_load()
    for day in range(2, History.history_depth + 1):
        page.fill_datepicker_date(datetime.now() - timedelta(day))
        page.wait_for_table_to_load(retries=450)
        assert page.count_entities() >= History.entities_per_day
        page.close_datepicker()
        # We allow failures since if we are on the same day there won't be an 'X' button
        page.clear_existing_date(allow_failures=True)


class TestHistory(TestBase):
    def test_history(self):
        _check_history_of_entity(self.devices_page)
        _check_history_of_entity(self.users_page)
