import logging
from datetime import datetime

import pytest
import pytz

from axonius.utils.parsing import parse_date_with_timezone
from ui_tests.tests.ui_test_base import TestBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f'axonius.{__name__}')

DATE_STRING_LENGTH = 10
DEFAULT_DATE_FORMAT = 'YYYY-MM-DD'


class TestGUISettings(TestBase):
    def test_date_format(self):
        try:
            self.base_page.run_discovery()
            self.settings_page.switch_to_page()
            self.settings_page.click_gui_settings()
            self.settings_page.set_date_format('MM-DD-YYYY')
            self.settings_page.click_save_gui_settings()
            self.dashboard_page.switch_to_page()

            # Check in dashboard lifecycle
            cycle_card = self.dashboard_page.get_lifecycle_card_info()
            complete_cycle_date = cycle_card['Last cycle completed at:'].strip()[:DATE_STRING_LENGTH]
            with pytest.raises(ValueError) as exception_info:
                datetime.strptime(complete_cycle_date, '%Y-%d-%m')
                assert exception_info.match(r'.*does\snot\smatch\sformat\s.*')
            assert isinstance(datetime.strptime(complete_cycle_date, '%m-%d-%Y'), datetime)

            # Check in StringView (Tables, etc)
            self.devices_page.switch_to_page()
            self.devices_page.edit_columns(add_col_names=['Fetch Time'])
            table_data = self.devices_page.get_all_data()
            # Take last column date only
            first_row_date = table_data[0].split('\n')[-1].strip()[:DATE_STRING_LENGTH]

            with pytest.raises(ValueError) as exception_info:
                datetime.strptime(first_row_date, '%Y-%d-%m')
                assert exception_info.match(r'.*does\snot\smatch\sformat\s.*')
            assert isinstance(datetime.strptime(first_row_date, '%m-%d-%Y'), datetime)
        except Exception as err:
            logger.info(f'Test failed with exception: {str(err)}', exc_info=True)
            raise
        finally:
            # Cleanup
            self.settings_page.switch_to_page()
            self.settings_page.click_gui_settings()
            self.settings_page.set_date_format(DEFAULT_DATE_FORMAT)
            self.settings_page.click_save_gui_settings()

    def test_datetime_in_localtime(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        cycle_card = self.dashboard_page.get_lifecycle_card_info()
        complete_cycle_date = cycle_card['Last cycle completed at:'].strip()
        # Make sure the lifecacle completed less then a minute ago in localtime
        israel_timezone = pytz.timezone('Israel')
        assert abs(
            (datetime.now(israel_timezone) - parse_date_with_timezone(complete_cycle_date, 'Israel')).total_seconds()
        ) < 60
