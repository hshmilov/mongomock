import pytest

from ui_tests.tests.ui_test_base import TestBase
from services.standalone_services.smtp_service import generate_random_valid_email
from services.standalone_services.maildiranasaurus_service import MaildiranasaurusService

ENFORCEMENT_NAME = 'lalala'
ENFORCEMENT_ACTION_NAME = 'send email please'


class TestEmailEnforce(TestBase):

    def _test_csv(self, recipient, smtp_service, devices_count):
        mail_content = smtp_service.wait_for_email_first_csv_content(recipient)
        mail_content_decoded = mail_content.decode('utf-8')
        mail_content_split = mail_content_decoded.split('\r\n')
        assert len(mail_content_split) == devices_count + 2, f'mail content: {mail_content}'
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.assert_csv_match_ui_data_with_content(mail_content)

    def _test_email_enforce(self, query_params):
        with MaildiranasaurusService().contextmanager(take_ownership=True, retry_if_fail=True) as smtp_service:
            self.settings_page.add_email_server(smtp_service.fqdn, smtp_service.port)

            recipient = generate_random_valid_email()

            self.base_page.run_discovery()

            self.enforcements_page.create_basic_enforcement(ENFORCEMENT_NAME)
            self.enforcements_page.add_main_action_send_email(ENFORCEMENT_ACTION_NAME,
                                                              recipient=recipient,
                                                              attach_csv=True)

            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()
            devices_count = self.devices_page.enforce_action_on_query(**query_params)

            smtp_service.verify_email_send(recipient)
            self._test_csv(recipient, smtp_service, devices_count)
            self.devices_page.reset_query()
        self.settings_page.remove_email_server()

    @pytest.mark.skip('AX-8509')
    def test_email_enforce_with_filtered_columns(self):
        self._test_email_enforce(dict(
            query=self.devices_page.VALUE_OS_WINDOWS,
            action=ENFORCEMENT_NAME,
            filter_column_data={
                'col_name':
                    self.devices_page.FIELD_HOSTNAME_TITLE,
                'filter_list': [{'term': 'win'}]
            }
        ))

    @pytest.mark.skip('Will probably fixed on AX-7472')
    def test_email_enforce_with_changed_columns(self):
        self._test_email_enforce(dict(
            query=self.devices_page.VALUE_OS_WINDOWS,
            action=ENFORCEMENT_NAME,
            add_col_names=[
                self.devices_page.FIELD_FETCH_TIME],
            remove_col_names=[
                self.devices_page.FIELD_OS_TYPE]
        ))
