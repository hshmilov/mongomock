from axonius.utils.wait import wait_until
from ui_tests.tests.ui_test_base import TestBase


class TestDevicesDefaultColumns(TestBase):

    def test_edit_system_default_columns(self):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()

        base_columns = self.devices_page.get_columns_header_text()
        system_default_columns = ['Adapter Connections', 'Host Name', 'Last Seen', 'Network Interfaces: MAC',
                                  'Network Interfaces: IPs', 'OS: Type', 'Tags']
        hostname_search_columns = ['Adapter Connections', 'Host Name', 'Last Seen', 'Last Used Users',
                                   'Network Interfaces: IPs', 'OS: Type',
                                   'Installed Software: Software Name and Version', 'Tags']
        system_default_hostname_search_columns = ['Adapter Connections', 'Host Name', 'Last Used Users',
                                                  'Network Interfaces: IPs', 'OS: Type',
                                                  'Installed Software: Software Name and Version', 'Tags']

        self.devices_page.open_edit_columns(system_default=True)
        wait_until(lambda: self.devices_page.get_edit_columns_modal_title() ==
                   self.devices_page.EDIT_SYSTEM_DEFAULT_TITLE)
        self.devices_page.remove_columns([self.devices_page.FIELD_ASSET_NAME])
        self.devices_page.close_edit_columns_save_system_default()
        assert self.devices_page.get_columns_header_text() == base_columns

        self.devices_page.open_edit_columns(system_default=True)
        self.devices_page.remove_columns([self.devices_page.FIELD_TAGS])
        self.devices_page.close_edit_columns_cancel_system_default()

        assert self.devices_page.get_columns_header_text() == base_columns
        self.devices_page.reset_columns_system_default()
        assert self.devices_page.get_columns_header_text() == system_default_columns
        self.devices_page.reset_columns_user_default()
        assert self.devices_page.get_columns_header_text() == base_columns

        self.devices_page.select_specific_search(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert self.devices_page.get_columns_header_text() == hostname_search_columns
        self.devices_page.open_edit_columns(system_default=True)
        wait_until(lambda: self.devices_page.get_edit_columns_modal_title() ==
                   self.devices_page.EDIT_SYSTEM_SEARCH_DEFAULT_HOSTNAME_TITLE)
        self.devices_page.remove_columns([self.devices_page.FIELD_LAST_SEEN])
        self.devices_page.close_edit_columns_save_system_default()
        assert self.devices_page.get_columns_header_text() == hostname_search_columns
        self.devices_page.reset_columns_system_default()
        assert self.devices_page.get_columns_header_text() == system_default_hostname_search_columns

        self.devices_page.refresh()
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.get_columns_header_text() == system_default_columns
        self.devices_page.select_specific_search(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert self.devices_page.get_columns_header_text() == system_default_hostname_search_columns
