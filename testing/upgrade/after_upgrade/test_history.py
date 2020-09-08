import time
from datetime import datetime, timedelta

from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import History


def _check_history_of_entity(page: EntitiesPage):
    page.switch_to_page()
    page.wait_for_table_to_load()
    for day in range(2, History.history_depth + 1):
        datepicker_date = datetime.now() - timedelta(day)
        print(f'day: {day} datepicker_date: {datepicker_date}')
        page.fill_datepicker_date(datepicker_date)
        page.wait_for_table_to_load(retries=450)
        assert page.count_entities() >= History.entities_per_day
        # We sleep so the 'X' button will react properly
        time.sleep(1)
        page.clear_existing_date(allow_failures=False)


class TestHistory(TestBase):
    def test_history(self):
        _check_history_of_entity(self.devices_page)
        _check_history_of_entity(self.users_page)
