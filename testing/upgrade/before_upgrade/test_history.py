import json
from pathlib import Path

from axonius.entities import EntityType
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import History


class TestPopulateHistory(TestBase):
    def test_populate_history(self):
        devices = self._create_history(EntityType.Devices, update_field=None, days_to_fill=History.history_depth)
        users = self._create_history(EntityType.Users, update_field=None, days_to_fill=History.history_depth)

        content = json.dumps({'devices': devices, 'users': users})
        Path(History.file_path).write_text(content)
