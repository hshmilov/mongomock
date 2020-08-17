from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.tests import ui_consts
from ui_tests.tests.test_dashboard_chart_base import TestDashboardChartBase
from ui_tests.tests.ui_consts import (HOSTNAME_DC_QUERY,
                                      HOSTNAME_DC_QUERY_NAME,
                                      IPS_192_168_QUERY,
                                      IPS_192_168_QUERY_NAME,
                                      OS_TYPE_OPTION_NAME)


class TestDashboardMyDashboard(TestDashboardChartBase):
    INTERSECTION_QUERY = f'({IPS_192_168_QUERY}) and ({HOSTNAME_DC_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY = f'({IPS_192_168_QUERY}) and not ({HOSTNAME_DC_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY = f'not (({IPS_192_168_QUERY}) or ({HOSTNAME_DC_QUERY}))'
    OSX_OPERATING_SYSTEM_FILTER = 'specific_data.data.os.type == "OS X"'
    OSX_OPERATING_SYSTEM_NAME = 'OS X Operating System'
    TEST_EMPTY_TITLE = 'test empty'

    NEW_ADMIN_USER = 'admin1'

    # test bug AX-8254 - My dashboard reorder deletes the other My dashboards
    def test_dashboard_intersection_chart(self):
        self.devices_page.create_saved_query(IPS_192_168_QUERY, IPS_192_168_QUERY_NAME)
        self.devices_page.create_saved_query(HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME)
        self.devices_page.create_saved_query(self.OSX_OPERATING_SYSTEM_FILTER, self.OSX_OPERATING_SYSTEM_NAME)

        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with duplicated Admin role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(self.NEW_ADMIN_USER,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.ADMIN_ROLE)
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.select_space(2)
        admin_chart1 = 'Admin 1'
        self.dashboard_page.add_intersection_card('Devices',
                                                  IPS_192_168_QUERY_NAME,
                                                  HOSTNAME_DC_QUERY_NAME,
                                                  admin_chart1)
        self.dashboard_page.wait_for_spinner_to_end()
        self.login_page.switch_user(self.NEW_ADMIN_USER, ui_consts.NEW_PASSWORD, None, False)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.select_space(2)
        new_admin_chart1 = 'New_Admin 1'
        new_admin_chart2 = 'New_Admin 2'
        self.dashboard_page.add_segmentation_card(module='Devices',
                                                  field=OS_TYPE_OPTION_NAME,
                                                  title=new_admin_chart1,
                                                  view_name=self.OSX_OPERATING_SYSTEM_NAME)
        self.dashboard_page.add_comparison_card([{'module': 'Devices', 'query': self.OSX_OPERATING_SYSTEM_NAME},
                                                 {'module': 'Devices', 'query': self.OSX_OPERATING_SYSTEM_NAME}],
                                                title=new_admin_chart2,
                                                chart_type='pie')
        new_admin_chart1_id = self.dashboard_page.get_dashboard_card_id(new_admin_chart1)
        new_admin_chart2_id = self.dashboard_page.get_dashboard_card_id(new_admin_chart2)
        space_id = self.dashboard_page.get_space_id(2)
        reorder_payload = {
            'spaceId': space_id,
            'panels_order': [new_admin_chart2_id, new_admin_chart1_id]
        }
        self.axonius_system.gui.login_user({'user_name': self.NEW_ADMIN_USER, 'password': ui_consts.NEW_PASSWORD})
        reorder_results = self.axonius_system.gui.reorder_dashboard(space_id, payload=reorder_payload)
        assert reorder_results.status_code == 200
        self.base_page.refresh()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.select_space(2)
        all_cards = self.dashboard_page.get_all_cards()
        assert len(all_cards) == 3
        assert self.dashboard_page.get_title_from_card(all_cards[0]) == new_admin_chart2
        assert self.dashboard_page.get_title_from_card(all_cards[1]) == new_admin_chart1
        self.login_page.switch_user(DEFAULT_USER['user_name'], DEFAULT_USER['password'])
        self.dashboard_page.switch_to_page()
        self.dashboard_page.select_space(2)
        # assert there are 2 cards, the add new chart and the previously added chart
        all_cards = self.dashboard_page.get_all_cards()
        assert len(all_cards) == 2
        assert self.dashboard_page.get_title_from_card(all_cards[0]) == admin_chart1
