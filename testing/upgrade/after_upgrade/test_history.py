import time
from datetime import datetime, timedelta
import json
from pathlib import Path

from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import History


def _check_history_of_entity(page: EntitiesPage, count_list):
    page.switch_to_page()
    page.wait_for_table_to_load()
    for day in range(1, History.history_depth):
        page.fill_showing_results(datetime.now() - timedelta(day))
        time.sleep(0.5)
        page.wait_for_table_to_load()
        assert page.count_entities() >= count_list[day - 1]
        page.close_showing_results()
        page.clear_showing_results()


class TestHistory(TestBase):
    def test_history(self):
        content = json.loads(Path(History.file_path).read_text())
        devices = content['devices']
        users = content['users']

        _check_history_of_entity(self.devices_page, devices)
        _check_history_of_entity(self.users_page, users)
