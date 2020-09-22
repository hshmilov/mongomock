from test_credentials.test_gui_credentials import AXONIUS_USER
from test_credentials.test_aws_credentials import client_details as aws_client_details
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AWS_ADAPTER_NAME, AWS_ADAPTER
from services.adapters.aws_service import AwsService
from services.plugins.compliance_service import ComplianceService


# pylint: disable=too-many-statements
class TestCloudComplianceComments(TestBase):

    def test_compliance_comments_filtering(self):
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.toggle_compliance_feature()

        with AwsService().contextmanager(take_ownership=True), \
                ComplianceService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[0][0])
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[3][0])

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.compliance_page.switch_to_page()

            self.compliance_page.open_accounts_filter_dropdown()
            accounts = self.compliance_page.get_all_accounts_options()

            # add comments to section 1.1
            self.compliance_page.click_specific_row_by_field_value('Section', '1.1')
            self.compliance_page.add_comment('comment 0', 'ax-dev2 (817364327683)')
            self.compliance_page.close_side_panel()

            # add comments to section 1.2
            self.compliance_page.click_specific_row_by_field_value('Section', '1.2')
            self.compliance_page.add_comment('comment 1', 'All')
            self.compliance_page.add_comment('comment 2', 'ax-dev1 (405773942477)')
            self.compliance_page.add_comment('comment 3', 'ax-dev1 (405773942477)')
            self.compliance_page.add_comment('comment 4', 'ax-dev2 (817364327683)')
            self.compliance_page.close_side_panel()

            # add comments to section 1.5
            self.compliance_page.click_specific_row_by_field_value('Section', '1.5')
            self.compliance_page.add_comment('comment 5', 'All')
            self.compliance_page.add_comment('comment 6', 'ax-dev1 (405773942477)')
            self.compliance_page.add_comment('comment 7', 'ax-dev2 (817364327683)')
            self.compliance_page.add_comment('comment 8', 'ax-dev2 (817364327683)')
            self.compliance_page.close_side_panel()

            # test tooltips on aggregated view both accounts
            self.compliance_page.assert_comment_tooltip(row=1, text='comment 0')
            self.compliance_page.assert_comment_tooltip(row=2, text='Rule has 4 comments')
            self.compliance_page.assert_comment_tooltip(row=5, text='Rule has 4 comments')

            self.compliance_page.assert_comment('Section', '1.1', 'comment 0\nax-dev2 (817364327683)')

            text = ','.join(['comment 4\nax-dev2 (817364327683)', 'comment 3\nax-dev1 (405773942477)',
                             'comment 2\nax-dev1 (405773942477)', 'comment 1\nAll'])
            self.compliance_page.assert_comment('Section', '1.2', text)

            text = ','.join(['comment 8\nax-dev2 (817364327683)', 'comment 7\nax-dev2 (817364327683)',
                             'comment 6\nax-dev1 (405773942477)', 'comment 5\nAll'])
            self.compliance_page.assert_comment('Section', '1.5', text)

            # test tooltips and comments not on aggregated view account ax-dev1 (405773942477)
            self.compliance_page.toggle_aggregated_view()
            self.compliance_page.open_accounts_filter_dropdown()
            self.compliance_page.toggle_filter(accounts[0])

            self.compliance_page.assert_comment_tooltip(row=1, text='')
            self.compliance_page.assert_comment_tooltip(row=2, text='Rule has 3 comments')
            self.compliance_page.assert_comment_tooltip(row=5, text='Rule has 2 comments')

            self.compliance_page.assert_comment('Section', '1.1', '')

            text = 'comment 3\nax-dev1 (405773942477),comment 2\nax-dev1 (405773942477),comment 1\nAll'
            self.compliance_page.assert_comment('Section', '1.2', text)

            self.compliance_page.assert_comment('Section', '1.5', 'comment 6\nax-dev1 (405773942477),comment 5\nAll')

            # test tooltips and comments not on aggregated view account ax-dev2 (817364327683)
            self.compliance_page.open_accounts_filter_dropdown()
            self.compliance_page.toggle_filter(accounts[0])
            self.compliance_page.toggle_filter(accounts[1])

            self.compliance_page.assert_comment_tooltip(row=1, text='comment 0')
            self.compliance_page.assert_comment_tooltip(row=2, text='Rule has 2 comments')
            self.compliance_page.assert_comment_tooltip(row=5, text='Rule has 3 comments')

            self.compliance_page.assert_comment('Section', '1.1', 'comment 0\nax-dev2 (817364327683)')

            self.compliance_page.assert_comment('Section', '1.2', 'comment 4\nax-dev2 (817364327683),comment 1\nAll')

            text = 'comment 8\nax-dev2 (817364327683),comment 7\nax-dev2 (817364327683),comment 5\nAll'
            self.compliance_page.assert_comment('Section', '1.5', text)

            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)

        self.wait_for_adapter_down(AWS_ADAPTER)
        self.settings_page.restore_feature_flags(True)

    def test_compliance_comments_add_edit_delete(self):
        with ComplianceService().contextmanager(take_ownership=True):
            self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
            self.settings_page.toggle_compliance_feature()
            self.compliance_page.switch_to_page()

            # test add comment
            self.compliance_page.click_specific_row_by_field_value('Section', '1.1')
            assert self.compliance_page.is_add_comment_button_disabled()
            self.compliance_page.fill_comment_text('text comment')
            assert self.compliance_page.is_add_comment_button_disabled()
            self.compliance_page.select_comment_account('All')
            assert not self.compliance_page.is_add_comment_button_disabled()
            self.compliance_page.save_new_comment()
            assert self.compliance_page.is_add_comment_button_disabled()

            # check inputs are empty now
            assert self.compliance_page.get_comment_text_input_value() == ''
            assert not self.compliance_page.is_select_comment_account_disabled()

            # test cancel edit comment
            assert self.driver.find_element_by_css_selector(
                self.compliance_page.COMMENT_TEXT_VALUE).text == 'text comment'
            self.compliance_page.edit_comment()
            assert self.compliance_page.is_add_comment_text_input_disabled()
            assert self.compliance_page.is_select_comment_account_disabled()

            self.compliance_page.assert_all_edit_and_delete_buttons_disabled()
            self.compliance_page.cancel_editing_comment()

            # test save edit comment
            self.compliance_page.assert_comment_text('text comment')
            self.compliance_page.edit_comment()

            self.compliance_page.fill_comment_text('text comment edited')
            self.compliance_page.update_comment()
            self.compliance_page.assert_comment_text('text comment edited')

            # test delete comment
            self.compliance_page.assert_comments_string('text comment edited\nAll')
            self.compliance_page.delete_comment()
            self.compliance_page.assert_comment_deleted()
            self.compliance_page.close_side_panel()
        self.settings_page.restore_feature_flags(True)

    def test_compliance_comments_permission(self):
        with ComplianceService().contextmanager(take_ownership=True):
            self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
            self.settings_page.toggle_compliance_feature()
            self.compliance_page.switch_to_page()
            self.compliance_page.click_specific_row_by_field_value('Section', '1.1')
            self.compliance_page.add_comment('comment 0', 'All')

            self.settings_page.add_user_with_duplicated_role(ui_consts.VIEWER_USERNAME,
                                                             ui_consts.NEW_PASSWORD,
                                                             ui_consts.FIRST_NAME,
                                                             ui_consts.LAST_NAME,
                                                             self.settings_page.VIEWER_ROLE)

            self.login_page.switch_user(ui_consts.VIEWER_USERNAME, ui_consts.NEW_PASSWORD)
            self.compliance_page.switch_to_page()
            self.compliance_page.wait_for_table_to_load()
            self.compliance_page.assert_comment('Section', '1.1', 'comment 0\nAll')
            self.compliance_page.click_specific_row_by_field_value('Section', '1.1')
            self.compliance_page.assert_cannot_add_edit_or_delete_comment()
