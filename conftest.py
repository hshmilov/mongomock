import pytest


def pytest_addoption(parser):
    def add_option(param_name, **kwargs):
        param_flag = f'--{param_name}'
        parser.addoption(param_flag, **kwargs)

    add_option('local-browser', action='store_true', default=False, help='Run with local-browser')
    add_option('sanity', action='store_true', default=False, help='Run only sanity tests')


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--sanity'):
        return
    skip_not_sanity = pytest.mark.skip(reason='Not a sanity test')
    for item in items:
        if 'sanity' not in item.keywords:
            item.add_marker(skip_not_sanity)
