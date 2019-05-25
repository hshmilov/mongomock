import time

from ui_tests.tests.instances_test_base import (NODE_MAKER_USERNAME,
                                                TestInstancesBase)


class TestInstancesBeforeNodeJoin(TestInstancesBase):

    def test_instances_user_before_join(self):
        self.put_customer_conf_file()

        # Test that user exists and we can connect to it
        self.check_instances_user_existance()

        self.check_instances_user_deletion_after_gui_login()

    def check_instances_user_existance(self):
        for instance in self._instances:
            self.connect_node_maker(instance)

    def check_instances_user_deletion_after_gui_login(self):
        # Test that node maker does not exist after login
        for instance in self._instances:
            assert NODE_MAKER_USERNAME in instance.ssh('cat /etc/passwd')[1]
            initial_base_url = self.base_url
            self.change_base_url(f'https://{instance.ip}')
            try:
                self.signup_page.wait_for_signup_page_to_load()
                self.signup_page.fill_signup_with_defaults_and_save()
                self.login_page.wait_for_login_page_to_load()
                self.login()
                time.sleep(61)
                assert NODE_MAKER_USERNAME not in instance.ssh('cat /etc/passwd')[1]
            finally:
                self.change_base_url(initial_base_url)
