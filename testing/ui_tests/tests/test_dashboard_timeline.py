import pytest

from axonius.entities import EntityType
from ui_tests.tests.ui_consts import MANAGED_DEVICES_QUERY_NAME, DEVICES_MODULE
from ui_tests.tests.ui_test_base import TestBase


class TestDashboardTimeline(TestBase):

    TIMELINE_CARD_TITLE = 'Timeline'

    @pytest.mark.skip('ad change')
    def test_disabled_history_warning(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self._create_history(EntityType.Devices, self.devices_page.FIELD_HOSTNAME_NAME)
        self.dashboard_page.refresh()

        self.dashboard_page.add_timeline_card(DEVICES_MODULE, MANAGED_DEVICES_QUERY_NAME, self.TIMELINE_CARD_TITLE)
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
