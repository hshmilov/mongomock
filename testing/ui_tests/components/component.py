import logging
import os


logger = logging.getLogger(f'axonius.{__name__}')


class Component:
    def __init__(self, driver, base_url, test_base, local_browser: bool):
        self.driver = driver
        self.base_url = base_url
        self.local_browser = local_browser
        self.ui_tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../', '../'))
        self.test_base = test_base
