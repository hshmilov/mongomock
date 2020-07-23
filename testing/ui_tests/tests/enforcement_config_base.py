from ui_tests.tests.ui_test_base import TestBase


class TestEnforcementConfigBase(TestBase):
    RECURRENCE_OPTIONS = ['Every discovery cycle', 'Every x days', 'Days of week', 'Days of month']
    ENFORCEMENT_CHANGE_NAME = 'test_enforcement_change'
    ENFORCEMENT_CHANGE_FILTER = 'adapters_data.json_file_adapter.test_enforcement_change == 5'
    FIELD_NAME = 'Name'
    FIELD_QUERY_NAME = 'Trigger Query Name'

    def _create_enforcement_change_query(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.run_filter_and_save(self.ENFORCEMENT_CHANGE_NAME, self.ENFORCEMENT_CHANGE_FILTER)
