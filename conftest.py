import pytest

# Browsers
from ui_tests.tests.ui_test_base import TestBase

CHROME = 'chrome'
FIREFOX = 'firefox'


def pytest_addoption(parser):
    def add_option(param_name, **kwargs):
        param_flag = f'--{param_name}'
        parser.addoption(param_flag, **kwargs)

    add_option('local-browser', action='store_true', default=False, help='Run with local-browser')
    add_option('sanity', action='store_true', default=False, help='Run only sanity tests')
    add_option('teardown-keep-db', action='store_true', default=False, help='Keep the DB at teardown')
    add_option('browser', action='store', default=CHROME, help='Choose browser')
    add_option('host-hub', action='store_true', default=False, help='Run with hub in host')
    add_option('export-name', action='store', default=None, help='An export name to use')


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    yield
    if not hasattr(item.session, 'last_testsfailed_status'):
        item.session.last_testsfailed_status = 0

    if item.session.testsfailed and item.session.testsfailed > item.session.last_testsfailed_status:
        TestBase.save_backup(item.name)
    item.session.last_testsfailed_status = item.session.testsfailed


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--sanity'):
        return
    skip_not_sanity = pytest.mark.skip(reason='Not a sanity test')
    for item in items:
        if 'sanity' not in item.keywords:
            item.add_marker(skip_not_sanity)
