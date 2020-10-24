from services.adapters.wmi_service import WmiService

from ui_tests.tests.test_dashboard_chart_base import TestDashboardChartBase
from ui_tests.tests.ui_consts import DEVICES_MODULE, VULNERABLE_SOFTWARE_FIELD_NAME, ADMIN_LOCAL_USERS_FIELD_NAME
from test_credentials.test_kaseya_credentials import KASEYA_DB_MOCK_WITH_VULNERABILITES


class TestDashboardSegmentationChart(TestDashboardChartBase):
    ENFORCEMENT_WMI_SEGMENTATION_QUERY_NAME = 'Test Local Admins Segmentation'
    TEST_LOCAL_ADMIN_SEGMENTATION_TITLE = 'Local Admin (adapterdata)'
    TEST_VULN_SW_SEGMENTATION_TITLE = 'Vulnerable Software (adapterdata)'

    ENFORCEMENT_WMI_SEGMENTATION_QUERY = '(specific_data.data.hostname == "22AD.TestDomain.test") or ' \
                                         '(specific_data.data.hostname == "WIN-I8QNMLDIKHR.TestDomain.test") or ' \
                                         '(specific_data.data.hostname == "WIN-VGICH0DQCH7.TestDomain.test")'

    LOCAL_ADMINS_ASSET_NAMES = [
        '22AD',
        'WIN-I8QNMLDIKHR',
        'WIN-VGICH0DQCH7']

    def test_segmentation_local_admin_users(self):
        with WmiService().contextmanager(take_ownership=True):
            self.enforcements_page.switch_to_page()
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement(
                self.ENFORCEMENT_WMI_SEGMENTATION_QUERY_NAME, self.ENFORCEMENT_WMI_SEGMENTATION_QUERY)
            self.base_page.run_discovery()
            self.dashboard_page.switch_to_page()
            self.dashboard_page.add_segmentation_card(module=DEVICES_MODULE,
                                                      field=ADMIN_LOCAL_USERS_FIELD_NAME,
                                                      title=self.TEST_LOCAL_ADMIN_SEGMENTATION_TITLE,
                                                      view_name=self.ENFORCEMENT_WMI_SEGMENTATION_QUERY_NAME,
                                                      include_empty=False)
            self.dashboard_page.wait_for_spinner_to_end()
            data_dict = self.dashboard_page.get_histogram_chart_values(self.TEST_LOCAL_ADMIN_SEGMENTATION_TITLE)

            for asset_name in self.LOCAL_ADMINS_ASSET_NAMES:
                assert int(data_dict[f'Administrator@{asset_name}']) == 1

    def test_vulnerable_software_segmentation(self):
        expected_values = {
            'PostgreSQL': 2,
            'Internet Explorer': 1,
            'Microsoft SQL Server': 1
        }

        db = self.axonius_system.get_devices_db()
        db.insert_many(KASEYA_DB_MOCK_WITH_VULNERABILITES)

        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card(module=DEVICES_MODULE,
                                                  field=VULNERABLE_SOFTWARE_FIELD_NAME,
                                                  title=self.TEST_VULN_SW_SEGMENTATION_TITLE,
                                                  include_empty=False)
        self.dashboard_page.wait_for_spinner_to_end()
        data_dict = self.dashboard_page.get_histogram_chart_values(self.TEST_VULN_SW_SEGMENTATION_TITLE)

        for value in expected_values:
            assert int(data_dict[value]) == expected_values[value]
