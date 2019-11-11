import pytest

from services.adapters.alertlogic_service import AlertlogicService
from services.adapters.aws_service import AwsService
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (ALERTLOGIC_ADAPTER,
                                      ALERTLOGIC_ADAPTER_NAME,
                                      AWS_ADAPTER,
                                      AWS_ADAPTER_NAME)


class TestDataForm(TestBase):

    def update_optinal_password_field(self, plugin_title: str, password_field: str):
        self.adapters_page.refresh()
        self.adapters_page.wait_for_adapter(plugin_title)
        self.adapters_page.click_adapter(plugin_title)
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.click_row()
        self.driver.find_element_by_id(password_field).clear()
        self.adapters_page.click_save()

    def sync_on_server_connection_failure(self, adapter_plugin_name, domain):
        self.adapters_page.wait_for_element_present_by_text(domain)
        self.adapters_page.wait_for_problem_connecting_to_server()
        self.adapters_page.refresh()
        self.adapters_page.wait_for_adapter(adapter_plugin_name)
        self.adapters_page.click_adapter(adapter_plugin_name)
        self.adapters_page.wait_for_element_present_by_text(domain)

    def verify_adapter_connection(self, kwargs):
        self.adapters_page.click_row()
        self.adapters_page.verify_creds(**kwargs)

    def verify_adapter_connection_and_save(self, kwargs):
        self.verify_adapter_connection(kwargs)
        self.adapters_page.click_save()

    def verify_adapter_connection_and_cancel(self, kwargs):
        self.verify_adapter_connection(kwargs)
        self.adapters_page.click_cancel()

    def test_alertlogicservice_default_data(self):

        adapter_input = {
            'domain': 'publicapi.alertlogic.axon.net',
            'apikey': 'rubbish',
            'https_proxy': '18.18.18.18',
            'verify_ssl': True
        }

        try:
            with AlertlogicService().contextmanager(take_ownership=True):
                self.adapters_page.creat_new_adapter_connection(plugin_title=ALERTLOGIC_ADAPTER_NAME,
                                                                adapter_input=adapter_input)
                self.sync_on_server_connection_failure(ALERTLOGIC_ADAPTER_NAME, adapter_input.get('domain'))
                self.verify_adapter_connection_and_save(adapter_input)
                self.sync_on_server_connection_failure(ALERTLOGIC_ADAPTER_NAME, adapter_input.get('domain'))
                self.verify_adapter_connection_and_cancel(adapter_input)

        finally:
            self.adapters_page.clean_adapter_servers(ALERTLOGIC_ADAPTER_NAME)
            self.wait_for_adapter_down(ALERTLOGIC_ADAPTER)

    def test_aws_default_data(self):

        adapter_input = {
            'region_name': 'US-EAST-2',
            'aws_access_key_id': '123456789',
            'account_tag': 'axonius',
            'aws_secret_access_key': '987654321',
            'get_all_regions': True
        }

        try:
            with AwsService().contextmanager(take_ownership=True):
                self.adapters_page.creat_new_adapter_connection(plugin_title=AWS_ADAPTER_NAME,
                                                                adapter_input=adapter_input)
                self.sync_on_server_connection_failure(AWS_ADAPTER_NAME, adapter_input.get('region_name'))
                self.verify_adapter_connection_and_save(adapter_input)
                self.sync_on_server_connection_failure(AWS_ADAPTER_NAME, adapter_input.get('region_name'))
                self.verify_adapter_connection_and_cancel(adapter_input)

        finally:
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)
            self.wait_for_adapter_down(AWS_ADAPTER)

    @pytest.mark.skip('AX-5367')
    def test_aws_clear_password_field(self):

        adapter_input = {
            'region_name': 'US-EAST-2',
            'aws_access_key_id': '123456789',
            'account_tag': 'axonius',
            'aws_secret_access_key': '987654321',
            'proxy': '10.10.10.10',
            'get_all_regions': True
        }

        try:
            with AwsService().contextmanager(take_ownership=True):
                self.adapters_page.creat_new_adapter_connection(plugin_title=AWS_ADAPTER_NAME,
                                                                adapter_input=adapter_input)
                self.sync_on_server_connection_failure(AWS_ADAPTER_NAME, adapter_input.get('region_name'))
                self.verify_adapter_connection_and_cancel(adapter_input)
                adapter_input['aws_secret_access_key'] = ''
                self.update_optinal_password_field(plugin_title=AWS_ADAPTER_NAME,
                                                   password_field='aws_secret_access_key')
                self.sync_on_server_connection_failure(AWS_ADAPTER_NAME, adapter_input.get('region_name'))
                self.verify_adapter_connection_and_cancel(adapter_input)

        finally:
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)
            self.wait_for_adapter_down(AWS_ADAPTER)
