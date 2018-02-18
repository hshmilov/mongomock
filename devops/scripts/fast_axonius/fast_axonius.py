import importlib
import inspect
import glob
import os


"""
    Read readme.md
"""


def fast_axonius():
    import services.adapters as adapters

    adapters_folder = os.path.dirname(inspect.getfile(adapters))
    testing_folder = os.path.normpath(os.path.join(adapters_folder, '..', '..'))
    os.chdir(testing_folder)

    from test_helpers.adapter_test_base import AdapterTestBase
    from services.axonius_service import get_service
    services = {}

    axonius_system = get_service()
    for ad_name, variable in axonius_system.get_all_adapters():
        # Initialize it
        service = variable()
        name = os.path.basename(service.service_dir)
        services[ad_name] = service

    plugins = {}
    for plugin in axonius_system.axonius_services:
        plugins[plugin.container_name] = plugin
    for plugin_name, variable in axonius_system.get_all_plugins():
        # Initialize it
        plugin = variable()
        plugins[plugin_name] = plugin

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
                        if not services[name].get_is_container_up():
                            print(f'Container {name} not running')
                            return
                        if services[name].clients():
                            print('A Client Already exists')
                        if isinstance(services[name].test.some_client_details, list):
                            for client in services[name].test.some_client_details:
                                services[name].add_client(client[0])
                        else:
                            services[name].add_client(services[name].test.some_client_details)

                    return set_client

                services[name].set_client = get_func(name)

    class AxTests(object):
        def __init__(self, services=services, plugins=plugins):
            self._services = services
            self._plugins = plugins

        def __repr__(self):
            return 'use variable \'ax\''

        def set_all_clients(self):
            for service in self._services.values():
                if not service.get_is_container_up():
                    continue
                service.set_client()

    ax = AxTests()
    for name, service in services.items():
        setattr(ax, name, service)
    for name, service in plugins.items():
        setattr(ax, name, service)
    return ax
