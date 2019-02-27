import time

from axonius.utils.wait import wait_until

from ui_tests.tests.ui_test_base import TestBase


class TestLinkUnlink(TestBase):
    FIND_TWO_DEVICES_QUERY = 'adapters_data.active_directory_adapter.hostname == "windows8.TestDomain.test" or ' \
                             'adapters_data.json_file_adapter.id == exists(true)'

    def test_link_unlink(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(TestLinkUnlink.FIND_TWO_DEVICES_QUERY)
        self.devices_page.enter_search()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == 2

        self.devices_page.select_all_page_rows_checkbox()
        self.devices_page.open_link_dialog()
        wait_until(lambda: 'You are about to link 2 devices.' in self.devices_page.read_delete_dialog())
        self.devices_page.confirm_link()
        wait_until(lambda: self.devices_page.count_entities() == 1)

        self.devices_page.select_all_page_rows_checkbox()
        # for some reason, the pop up for "devices were linked" can be opened still or opened now
        time.sleep(10)
        self.devices_page.open_unlink_dialog()
        wait_until(lambda: 'You are about to unlink 1 devices.' in self.devices_page.read_delete_dialog())
        self.devices_page.confirm_link()
        wait_until(lambda: self.devices_page.count_entities() == 2)
