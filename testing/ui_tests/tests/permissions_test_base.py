import pytest
from selenium.common.exceptions import NoSuchElementException

from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase


def _check_for_no_access_status_code(result):
    return result.status_code == 401


class PermissionsTestBase(TestBase):
    TEST_SPACE_NAME = 'test space'
    TEST_REPORT_NAME = 'testonius'
    MY_DASHBOARD_TITLE = 'My Dashboard'
    CHART_MOCK_DATA = {
        'metric': 'segment',
        'view': 'histogram',
        'name': 'test_chart_failure',
        'config': {
            'entity': 'devices',
            'view': '',
            'field': {
                'name': 'specific_data.data.name',
                'title': 'Asset Name',
                'type': 'string'
            },
            'value_filter': [
                {
                    'name': '',
                    'value': ''
                }
            ],
            'sort': {
                'sort_by': 'value',
                'sort_order': 'desc'
            },
            'show_timeline': False,
            'timeframe': {
                'type': 'relative',
                'unit': 'day',
                'count': 7
            }
        }
    }

    def _add_action_to_role_and_login_with_user(self,
                                                permissions,
                                                category,
                                                add_action,
                                                role,
                                                user_name,
                                                password,
                                                wait_for_getting_started=True):
        self.login_page.logout_and_login_with_admin(wait_for_getting_started)
        if not permissions.get(category):
            permissions[category] = []
        permissions[category].append(add_action)
        self.settings_page.update_role(role, permissions, True)
        self.login_page.switch_user(user_name,
                                    password,
                                    None,
                                    wait_for_getting_started=wait_for_getting_started)

    def _assert_viewer_role(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(ui_consts.AD_ADAPTER_NAME)
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.assert_new_server_button_is_disabled()
        self.enforcements_page.switch_to_page()
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.find_new_enforcement_button()
        self.reports_page.switch_to_page()
        with pytest.raises(NoSuchElementException):
            self.reports_page.find_new_report_button()
        self.reports_page.is_disabled_new_report_button()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.users_page.click_row()
        with pytest.raises(NoSuchElementException):
            self.devices_page.add_new_tags([ui_consts.TAG_NAME])
        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_load()
        self.users_page.click_row()
        with pytest.raises(NoSuchElementException):
            self.devices_page.add_new_tags([ui_consts.TAG_NAME])
        self.instances_page.switch_to_page()
        self.instances_page.wait_for_table_to_load()
        assert self.instances_page.is_connect_node_disabled()
        self.settings_page.assert_screen_is_restricted()

    def _get_card_space_id(self, panel_id):
        return self.axonius_system.gui.get_space_id_from_panel(panel_id).get('space')

    def _try_to_fail_add_panel_to_restricted_space(self, user_name, password, space_id):
        self.axonius_system.gui.login_user({'user_name': user_name, 'password': password})
        result = self.axonius_system.gui.add_panel(space_id, self.CHART_MOCK_DATA)
        assert _check_for_no_access_status_code(result)

    def _try_to_fail_edit_panel_from_restricted_space(self, user_name, password, panel_id):
        self.axonius_system.gui.login_user({'user_name': user_name, 'password': password})
        result = self.axonius_system.gui.edit_panel(panel_id, self.CHART_MOCK_DATA)
        assert _check_for_no_access_status_code(result)

    def _try_to_fail_remove_panel_from_restricted_space(self, user_name, password, panel_id, space_id):
        self.axonius_system.gui.login_user({'user_name': user_name, 'password': password})
        result = self.axonius_system.gui.remove_panel(panel_id, space_id)
        assert _check_for_no_access_status_code(result)

    def _try_to_fail_move_panel_to_restricted_space(self, user_name, password, panel_id, space_id):
        self.axonius_system.gui.login_user({'user_name': user_name, 'password': password})
        result = self.axonius_system.gui.move_panel(panel_id, space_id)
        assert _check_for_no_access_status_code(result)
