from ui_tests.tests.ui_test_base import TestBase


class TestInstanceMetrics(TestBase):

    def test_instance_metrics_sanity(self):
        self.instances_page.switch_to_page()
        self.instances_page.click_query_row_by_name('Master')

        assert self.instances_page.find_instance_name_textbox().is_enabled()
        assert self.instances_page.find_instance_hostname_textbox().is_enabled()
        assert self.instances_page.get_save_button().is_enabled()

        items = self.instances_page.get_instance_metrics_items()
        for [key, value] in items:
            assert value and value != '0'
            if 'Last Historical Snapshot' in key:
                # before cycle, there should be no data at all.
                assert int(value) == 0
        self.instances_page.close_instance_side_panel()

        self.base_page.run_discovery()

        self.instances_page.click_query_row_by_name('Master')
        items = self.instances_page.get_instance_metrics_items()
        for [key, value] in items:
            assert value and value != '0'
            if 'Last Historical Snapshot' in key:
                # After cycle, we expect to have a size for the latest snapshot taken.
                assert int(value) > 0
