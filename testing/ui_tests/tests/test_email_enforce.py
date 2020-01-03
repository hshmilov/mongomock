from ui_tests.tests.ui_test_base import TestBase
from services.standalone_services.smtp_service import SmtpService, generate_random_valid_email

ENFORCEMENT_NAME = 'lalala'
ENFORCEMENT_ACTION_NAME = 'send email please'
QUERY = 'Windows'


class TestEmailEnforce(TestBase):
    def test_email_enforce(self):
        with SmtpService().contextmanager(take_ownership=True) as smtp_service:
            self.settings_page.add_email_server(smtp_service.fqdn, smtp_service.port)

            recipient = generate_random_valid_email()

            self.base_page.run_discovery()

            self.enforcements_page.create_basic_enforcement(ENFORCEMENT_NAME, trigger=False)
            self.enforcements_page.add_main_action_send_email(ENFORCEMENT_ACTION_NAME, recipient=recipient)

            self.devices_page.switch_to_page()
            self.devices_page.enforce_action_on_query(QUERY, ENFORCEMENT_NAME)

            smtp_service.verify_email_send(recipient)

        self.settings_page.remove_email_server()
