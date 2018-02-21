import inspect
import subprocess
from datetime import datetime, timedelta
import importlib
import time
import glob
import os

import services
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.device import NETWORK_INTERFACES_FIELD
from services import adapters
from services.execution_service import ExecutionService
from services.aggregator_service import AggregatorService
from services.axon_service import TimeoutException
from services.core_service import CoreService
from services.gui_service import GuiService
from services.mongo_service import MongoService
from services.plugin_service import AdapterService, PluginService
from test_helpers.parallel_runner import ParallelRunner
from test_helpers.utils import try_until_not_thrown


def get_service():
    return AxoniusService()


class AxoniusService(object):
    def __init__(self):
        self.db = MongoService()
        self.core = CoreService()
        self.aggregator = AggregatorService()
        self.gui = GuiService()
        self.execution = ExecutionService()

        self.axonius_services = [self.db, self.core, self.aggregator, self.gui, self.execution]

    def stop(self, should_delete):
        # Not critical but lets stop in reverse order
        async_items = []
        for service in self.axonius_services[::-1]:
            current = iter(service.stop_async(should_delete=should_delete))
            next(current)  # actual stop call
            async_items.append(current)
        # stop_async is a generator that yields just after the first exec, that is why we run next(current) before
        # adding it to async_items; and after we go over all services, we need to complete the rest of the function
        # using next (in the 'for _ in async_item')
        for async_item in async_items:
            for _ in async_item:
                pass

    def take_process_ownership(self):
        for service in self.axonius_services:
            service.take_process_ownership()

    def start_and_wait(self, mode='', allow_restart=False, rebuild=False, skip=False):
        if rebuild:
            for service in self.axonius_services:
                service.remove_image()

        if allow_restart:
            for service in self.axonius_services:
                service.remove_container()

        # Start in parallel
        for service in self.axonius_services:
            if skip and service.get_is_container_up():
                continue
            service.start(mode=mode, allow_restart=allow_restart)

        # wait for all
        for service in self.axonius_services:
            service.wait_for_service()

    def get_devices_db(self):
        return self.db.get_devices_db(self.aggregator.unique_name)

    def insert_device(self, device_data):
        self.get_devices_db().insert_one(device_data)

    def get_devices_with_condition(self, cond):
        cursor = self.get_devices_db().find(cond)
        return list(cursor)

    def get_device_by_id(self, adapter_name, device_id):
        cond = {'adapters.data.id': device_id, 'adapters.plugin_unique_name': adapter_name}
        return self.get_devices_with_condition(cond)

    def get_device_network_interfaces(self, adapter_name, device_id):
        device = self.get_device_by_id(adapter_name, device_id)
        adapter_device = next(adapter_device for adapter_device in device[0]['adapters'] if
                              adapter_device[PLUGIN_UNIQUE_NAME] == adapter_name)
        return adapter_device['data'][NETWORK_INTERFACES_FIELD]

    def assert_device_aggregated(self, adapter, client_id, some_device_id, max_tries=30):
        self.aggregator.query_devices(adapter_id=adapter.unique_name)  # send trigger to agg to refresh devices
        devices_as_dict = adapter.devices()
        assert client_id in devices_as_dict

        # check the device is read by adapter
        devices_list = devices_as_dict[client_id]['parsed']
        assert len(list(filter(lambda device: device['id'] == some_device_id, devices_list))) == 1

        # check that the device is collected by aggregator and now in db

        def assert_device_inserted():
            devices = self.get_device_by_id(adapter.unique_name, some_device_id)
            assert len(devices) == 1

        try_until_not_thrown(max_tries, 10, assert_device_inserted)

    def restart_plugin(self, plugin):
        """
        :param plugin: plugint to restart
        note: restarting plugin does not delete its volume
        """
        plugin.stop(should_delete=False)
        plugin.start_and_wait()
        assert plugin.is_plugin_registered(self.core)

    def restart_core(self):
        self.core.stop()
        # Check that Aggregator really went down
        current_time = datetime.now()
        self.aggregator.trigger_check_registered()
        while self.aggregator.is_up():
            assert datetime.now() - current_time < timedelta(seconds=10)
            time.sleep(1)
        # Now aggregator is down as well
        self.core.start_and_wait()

        def assert_aggregator_registered():
            assert self.aggregator.is_up()
            assert self.aggregator.is_plugin_registered(self.core)

        try_until_not_thrown(30, 1, assert_aggregator_registered)

    @staticmethod
    def get_plugin(name):
        module = importlib.import_module(f"services.{name.lower()}_service")
        for variable_name in dir(module):
            variable = getattr(module, variable_name)
            if isinstance(variable, type) and ((issubclass(variable, PluginService) and variable != PluginService) or
                                               (issubclass(variable, MongoService))):
                return variable()
        raise ValueError('Plugin not found')

    @staticmethod
    def get_adapter(name):
        module = importlib.import_module(f"services.adapters.{name.lower()}_service")
        for variable_name in dir(module):
            variable = getattr(module, variable_name)
            if isinstance(variable, type) and issubclass(variable, AdapterService) and variable != AdapterService:
                return variable()
        raise ValueError('Adapter not found')

    def start_plugins(self, adapter_names, plugin_names, mode='', allow_restart=False, rebuild=False, hard=False,
                      skip=False):
        plugins = [self.get_adapter(name) for name in adapter_names] + [self.get_plugin(name) for name in plugin_names]
        if rebuild:
            for plugin in plugins:
                plugin.remove_image()
        if hard:
            for plugin in plugins:
                plugin.remove_volume()
        if allow_restart:
            for plugin in plugins:
                plugin.remove_container()
        for plugin in plugins:
            plugin.take_process_ownership()
            if skip and plugin.get_is_container_up():
                continue
            plugin.start(mode, allow_restart=allow_restart)
        timeout = 60
        start = time.time()
        first = True
        while start + timeout > time.time() and len(plugins) > 0:
            for plugin in plugins.copy():
                try:
                    plugin.wait_for_service(5 if first else 1)
                    plugins.remove(plugin)
                except TimeoutException:
                    pass
                first = False
        if len(plugins) > 0:
            # plugins contains failed ones and should be removed to make sure the state is stable for next time.
            for plugin in plugins:
                plugin.stop(should_delete=True)
            raise TimeoutException(repr([plugin.container_name for plugin in plugins]))

    def stop_plugins(self, adapter_names, plugin_names, should_delete):
        plugins = [self.get_adapter(name) for name in adapter_names] + [self.get_plugin(name) for name in plugin_names]
        async_items = []
        for plugin in plugins:
            plugin.take_process_ownership()
            current = iter(plugin.stop_async(should_delete=should_delete))
            next(current)  # actual stop call
            async_items.append(current)
        # stop_async is a generator that yields just after the first exec, that is why we run next(current) before
        # adding it to async_items; and after we go over all services, we need to complete the rest of the function
        # using next (in the 'for _ in async_item')
        for async_item in async_items:
            for _ in async_item:
                pass

    def remove_plugin_containers(self, adapter_names, plugin_names):
        plugins = [self.get_adapter(name) for name in adapter_names] + [self.get_plugin(name) for name in plugin_names]
        for plugin in plugins:
            plugin.remove_container()

    def get_all_plugins(self):
        plugins_folder = os.path.dirname(inspect.getfile(services))
        plugin_regex = os.path.join(plugins_folder, '*_service.py')
        plugins_list = []

        for plugin_path in glob.glob(plugin_regex):
            module_name = os.path.basename(plugin_path)[:-3]
            if module_name == '__init__':
                continue
            module = importlib.import_module(f'services.{module_name}')
            # Iterate variables and look for the service
            for variable_name in dir(module):
                variable = getattr(module, variable_name)
                if isinstance(variable, type) and ((issubclass(variable, PluginService) and variable != PluginService
                                                    and variable != AdapterService) or
                                                   (issubclass(variable, MongoService))):
                    not_internal = True
                    for service in self.axonius_services:
                        if isinstance(service, variable):
                            not_internal = False
                            break
                    if not_internal:
                        plugins_list.append((module_name[:-len('_service')], variable))
                        break
        return plugins_list

    @staticmethod
    def get_all_adapters():
        adapters_folder = os.path.dirname(inspect.getfile(adapters))
        adapter_regex = os.path.join(adapters_folder, '*_service.py')
        adapters_list = []

        for adapter_path in glob.glob(adapter_regex):
            module_name = os.path.basename(adapter_path)[:-3]
            if module_name == '__init__':
                continue
            module = importlib.import_module(f'services.adapters.{module_name}')
            # Iterate variables and look for the service
            for variable_name in dir(module):
                variable = getattr(module, variable_name)
                if isinstance(variable, type) and issubclass(variable, AdapterService) and variable != AdapterService:
                    adapters_list.append((module_name[:-len('_service')], variable))
                    break
        return adapters_list

    def build_libs(self, rebuild=False):
        image_name = 'axonius/axonius-libs'
        output = subprocess.check_output(['docker', 'images', image_name]).decode('utf-8')
        image_exists = image_name in output
        if image_exists:
            if rebuild:
                subprocess.call(['docker', 'rmi', image_name, '--force'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                print('Image axonius-libs already built - skipping build step')
                return
        runner = ParallelRunner()
        runner.append_single('axonius-libs', ['docker', 'build', '.', '-t', image_name],
                             cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'plugins',
                                                              'axonius-libs')))
        assert runner.wait_for_all() == 0

    def build(self, system, adapter_names, plugin_names, mode='', rebuild=False, hard=False, async=True):
        to_build = [self.get_adapter(name) for name in adapter_names] + [self.get_plugin(name) for name in plugin_names]
        if system:
            to_build = self.axonius_services + to_build
        if rebuild:
            for service in to_build:
                service.remove_image()
        if hard:
            for service in to_build:
                service.remove_volume()
        if async and len(to_build) > 1:
            runner = ParallelRunner()
            for service in to_build:
                if service.get_image_exists():
                    continue
                service.build(mode, runner)
                time.sleep(1)  # We are getting resource busy. we suspect this is due parallel build storm
            assert runner.wait_for_all() == 0
        else:
            for service in to_build:
                service.build(mode)
