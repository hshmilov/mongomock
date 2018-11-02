import subprocess
import shlex

from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase


class TestPrepareUsers(TestBase):
    def test_hidden_user(self):
        cortex_root = self.axonius_system.gui.cortex_root_dir
        # note: this is how chef invokes this script. if you touch anything here, you must update chef as well
        path_to_script = 'devops/scripts/migration/add_master_password.sh'
        subprocess.run(shlex.split(f'{path_to_script} {ui_consts.HIDDEN_USER_NEW_PASSWORD}'), cwd=cortex_root)

    def test_local_user(self):
        self.settings_page.switch_to_page()
        self.settings_page.wait_for_spinner_to_end()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME)

        self.settings_page.wait_for_user_created_toaster()

        self.settings_page.select_permissions('Adapters', self.settings_page.READ_ONLY_PERMISSION)
        self.settings_page.click_save_manage_users_settings()
        self.settings_page.wait_for_user_permissions_saved_toaster()
