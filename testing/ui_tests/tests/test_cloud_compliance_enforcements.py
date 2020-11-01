from test_credentials.test_gui_credentials import AXONIUS_USER, DEFAULT_USER
from test_credentials.test_aws_credentials import client_details as aws_client_details
from test_credentials.test_okta_credentials import client_details as okta_client_details
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AWS_ADAPTER_NAME, AWS_ADAPTER, OKTA_ADAPTER_NAME, OKTA_ADAPTER
from services.adapters.aws_service import AwsService
from services.adapters.okta_service import OktaService
from services.standalone_services.maildiranasaurus_service import MaildiranasaurusService
from services.standalone_services.smtp_service import generate_random_valid_email


class TestCloudComplianceEnforcements(TestBase):

    ENFORCE_BY_MAIL_TITLE = 'CAC Enforce By Mail Test'
    CAC_AGGREGATED_EMAIL_ADDRESS = 'test@avigdor55254b7c493d450499bd95598f548f5d.me'
    AWS_ADAPTER_USER_SETTINGS = 'Fetch information about IAM Users'
    AWS_ADAPTER_ROLE_SETTINGS = 'Fetch IAM roles as users'

    def test_cloud_compliance_ec_lock(self):
        self.login_page.logout_and_login_with_admin()
        self.settings_page.toggle_enforcement_feature_tag(False)

        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.enable_and_display_compliance()
        self.settings_page.save_and_wait_for_toaster()

        self.compliance_page.switch_to_page()
        self.compliance_page.click_enforce_menu()
        assert self.compliance_page.is_enforcement_lock_modal_visible()
        self.compliance_page.close_feature_lock_tip()
        assert not self.compliance_page.is_enforcement_lock_modal_visible()

        self.settings_page.toggle_enforcement_feature_tag(True)
        self.compliance_page.switch_to_page()
        self.compliance_page.click_enforce_menu()
        assert self.compliance_page.is_enforcement_actions_menu_visible()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=DEFAULT_USER['user_name'], password=DEFAULT_USER['password'])

    def _enforce_by_mail(self, recipient, send_to_admins=True):
        self.compliance_page.switch_to_page()
        self.compliance_page.wait_for_table_to_be_responsive()
        self.compliance_page.open_email_dialog()
        self.compliance_page.fill_enforce_by_mail_form(self.ENFORCE_BY_MAIL_TITLE,
                                                       recipient=recipient,
                                                       send_to_admins=send_to_admins)

    def test_compliance_email_enforce(self):
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.toggle_compliance_feature()

        with AwsService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            # set ax-dev2 to verify csv of ax-dev2 won't sent to aw-dev3 admin.
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[2][0])
            # set ax-dev3 account, this account has an admin user with a correlated email between okta and aws.
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[3][0])
            self.adapters_page.wait_for_server_green()

            self.adapters_page.switch_to_page()
            with OktaService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(OKTA_ADAPTER_NAME)
                self.adapters_page.create_new_adapter_connection(OKTA_ADAPTER_NAME, okta_client_details)
                self.adapters_page.wait_for_server_green()

                with MaildiranasaurusService().contextmanager(take_ownership=True, retry_if_fail=True) as smtp_service:
                    self.settings_page.add_email_server(smtp_service.fqdn, smtp_service.port)
                    self.settings_page.switch_to_page()
                    self.base_page.run_discovery()

                    recipient = generate_random_valid_email()
                    self._enforce_by_mail(recipient, send_to_admins=False)
                    smtp_service.verify_email_send(recipient)

                    self.adapters_page.switch_to_page()
                    self.adapters_page.click_adapter(AWS_ADAPTER_NAME)
                    self.adapters_page.click_advanced_settings()
                    self.adapters_page.click_aws_advanced_configuration()
                    self.adapters_page.click_toggle_button(
                        self.adapters_page.find_checkbox_by_label(self.AWS_ADAPTER_USER_SETTINGS),
                        make_yes=True)
                    self.adapters_page.click_toggle_button(
                        self.adapters_page.find_checkbox_by_label(self.AWS_ADAPTER_ROLE_SETTINGS),
                        make_yes=True)
                    self.adapters_page.save_advanced_settings()

                    # now, admins should get the email as well.
                    self.base_page.run_discovery()
                    self.compliance_page.switch_to_page()
                    self.compliance_page.toggle_aggregated_view()
                    self._enforce_by_mail(recipient)
                    smtp_service.verify_email_send(self.CAC_AGGREGATED_EMAIL_ADDRESS)
                    mail_content = smtp_service.wait_for_email_first_csv_content(self.CAC_AGGREGATED_EMAIL_ADDRESS)
                    mail_content_decoded = mail_content.decode('utf-8')
                    mail_content_split = mail_content_decoded.split('\r\n')
                    # 43 rules. and +2 for titles and last empty row.
                    assert len(mail_content_split) == 45, f'mail content: {mail_content!r}'

                self.settings_page.remove_email_server()
                self.adapters_page.switch_to_page()
                self.adapters_page.clean_adapter_servers(OKTA_ADAPTER_NAME)

            self.wait_for_adapter_down(OKTA_ADAPTER)
            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)

        self.wait_for_adapter_down(AWS_ADAPTER)
        self.settings_page.restore_feature_flags(True)
