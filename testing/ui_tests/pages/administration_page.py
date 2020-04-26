import boto3

from axonius.utils.wait import wait_until
from test_credentials.test_aws_credentials import EC2_ECS_EKS_READONLY_ACCESS_KEY_ID, \
    EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY
from ui_tests.pages.page import Page


class AdministrationPage(Page):
    ROOT_CSS = '.x-page .x-administration'
    UPLOAD_FILE_INPUT_CSS = '.filepond--browser'
    EXECUTE_SCRIPT_BUTTON_ID = 'execute_script'
    AXONIUS_CI_TESTS_BUCKET = 'axonius-ci-tests'

    @property
    def root_page_css(self):
        return self.ROOT_CSS

    @property
    def url(self):
        return f'{self.base_url}/administration'

    def switch_to_page(self):
        self.driver.get(self.url)

    def wait_for_upload_file_finish(self):
        wait_until(self._check_execution_button_status, total_timeout=240, interval=5)

    def get_execution_button(self):
        return self.driver.find_element_by_id(self.EXECUTE_SCRIPT_BUTTON_ID)

    def _check_execution_button_status(self):
        button = self.get_execution_button()
        return not self.is_element_disabled(button)

    def upload_configuration_script(self, file_name):
        s3_client = boto3.client(
            's3',
            aws_access_key_id=EC2_ECS_EKS_READONLY_ACCESS_KEY_ID,
            aws_secret_access_key=EC2_ECS_EKS_READONLY_SECRET_ACCESS_KEY
        )
        response = s3_client.get_object(Bucket=self.AXONIUS_CI_TESTS_BUCKET, Key=file_name)
        file_stream = response['Body'].read()
        input_id = self.driver.find_element_by_css_selector(self.UPLOAD_FILE_INPUT_CSS).get_attribute('id')
        self.upload_file_by_id(input_id, file_stream, is_bytes=True)
        self.wait_for_upload_file_finish()

    def execute_configuration_script(self):
        self.get_execution_button().click()
        self.wait_for_toaster('Script execution has begun')
