def pytest_addoption(parser):
    def add_option(param_name, **kwargs):
        param_flag = f'--{param_name}'
        parser.addoption(param_flag, **kwargs)

    add_option('local-browser', action='store_true', default=False, help='Run with local-browser')
