import importlib
import inspect
import glob
import os


"""
    Read readme.md
"""


def fast_axonius():
    import services.adapters as adapters
    from services.plugin_service import AdapterService

    adapters_folder = os.path.dirname(inspect.getfile(adapters))
    testing_folder = os.path.normpath(os.path.join(adapters_folder, '..', '..'))
    os.chdir(testing_folder)

    from test_helpers.adapter_test_base import AdapterTestBase
    adapter_regex = os.path.join(adapters_folder, '*.py')
    services = {}

    # Load each (service) module under the adapters_folder
    for adapter_path in glob.glob(adapter_regex):
        module_name = os.path.basename(adapter_path)[:-3]
        if module_name == '__init__':
            continue
        module = importlib.import_module(f'services.adapters.{module_name}')
        # Iterate variables and look for the service
        for variable_name in dir(module):
            variable = getattr(module, variable_name)
            if isinstance(variable, type) and issubclass(variable, AdapterService) and variable != AdapterService:
                # Initialize it
                service = variable()
                name = os.path.basename(service.service_dir)
                assert name.endswith('-adapter')
                name = name[:-len('-adapter')].replace('-', '_')
                services[name] = service

    parallel_tests = os.path.join(testing_folder, 'parallel_tests')
    adapter_tests_regex = os.path.join(parallel_tests, '*.py')

    # Load each (test) module under the adapters_tests_folder
    for adapter_test in glob.glob(adapter_tests_regex):
        module_name = os.path.basename(adapter_test)[:-3]
        if module_name == '__init__':
            continue
        module = importlib.import_module(f'parallel_tests.{module_name}')
        # Iterate variables and look for the test class
        for variable_name in dir(module):
            variable = getattr(module, variable_name)
            if isinstance(variable, type) and issubclass(variable, AdapterTestBase) and variable != AdapterTestBase:
                # Initialize it
                test = variable()
                name = test.adapter_name
                assert name.endswith('_adapter')
                name = name[:-len('_adapter')]
                if name not in services:
                    print(f'missing service for test {variable_name} in module {module_name}')
                services[name].test = test

                # Create a set_client with credentials function for that adapter's name
                def get_func(name):
                    def set_client():
                        if services[name].clients():
                            print('A Client Already exists')
                        services[name].add_client(services[name].test.some_client_details)

                    return set_client

                services[name].set_client = get_func(name)

    class AxTests(object):
        def __init__(self, services=services):
            self._services = services

        def __repr__(self):
            return 'use variable \'ax\''

    ax = AxTests()
    for name, service in services.items():
        setattr(ax, name, service)
    return ax
