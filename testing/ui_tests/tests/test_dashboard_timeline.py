from axonius.entities import EntityType
from test_credentials.test_gui_credentials import DEFAULT_USER
from test_helpers.dashboard_helper import assert_desc_sort_by_value
from ui_tests.tests.ui_consts import MANAGED_DEVICES_QUERY_NAME, DEVICES_MODULE
from ui_tests.tests.ui_test_base import TestBase


class TestDashboardTimeline(TestBase):

    TIMELINE_CARD_TITLE = 'Timeline'

    def _init_timeline_card_test(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self._create_history(EntityType.Devices, self.devices_page.FIELD_HOSTNAME_NAME)
        self.dashboard_page.refresh()

        self.dashboard_page.add_timeline_card(DEVICES_MODULE, MANAGED_DEVICES_QUERY_NAME, self.TIMELINE_CARD_TITLE)

    def test_disabled_history_warning(self):
        self._init_timeline_card_test()

        card = self.dashboard_page.get_card(self.TIMELINE_CARD_TITLE)
        self.dashboard_page.assert_timeline_svg_exist(card)

        self.settings_page.save_daily_historical_snapshot(False)
        self.dashboard_page.switch_to_page()
        card = self.dashboard_page.get_card(self.TIMELINE_CARD_TITLE)
        self.dashboard_page.assert_timeline_svg_exist(card)
        self.dashboard_page.verify_chart_warning_exists(card)

        self.settings_page.save_daily_historical_snapshot()
        self.dashboard_page.switch_to_page()
        card = self.dashboard_page.get_card(self.TIMELINE_CARD_TITLE)
        self.dashboard_page.assert_timeline_svg_exist(card)
        self.dashboard_page.verify_chart_warning_missing(card)

    def test_timeline_export_csv(self):
        self._init_timeline_card_test()

        card = self.dashboard_page.get_card(self.TIMELINE_CARD_TITLE)
        card_id = card.get_property('id')
        self.axonius_system.gui.login_user(DEFAULT_USER)
        csv_data = self.axonius_system.gui.get_chart_csv(card_id)
        all_csv_rows = csv_data.content.decode('utf-8').split('\r\n')
        csv_data_rows = [x.split(',') for x in all_csv_rows[1:-1]]
        csv_dates = [x[0] for x in csv_data_rows]
        assert_desc_sort_by_value(csv_dates)
        chart_ui_data = self.dashboard_page.get_data_from_timeline_card(card)
        for day in csv_data_rows:
            assert chart_ui_data[day[0]] == day[1:]
