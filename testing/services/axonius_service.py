import inspect
import subprocess
from datetime import datetime, timedelta
import importlib
import time
import glob
import os

from axonius.plugin_base import EntityType

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD
from services import adapters
from services import plugins
from services.plugins.execution_service import ExecutionService
from services.plugins.aggregator_service import AggregatorService
from services.axon_service import TimeoutException
from services.plugins.core_service import CoreService
from services.plugins.gui_service import GuiService
from services.plugins.reports_service import ReportsService
from services.plugins.static_correlator_service import StaticCorrelatorService
from services.plugins.system_scheduler_service import SystemSchedulerService
from services.plugins.mongo_service import MongoService
from test_helpers.parallel_runner import ParallelRunner
from test_helpers.utils import try_until_not_thrown


def get_service():
    return AxoniusService()


class AxoniusService(object):
    _NETWORK_NAME = 'axonius'

    def __init__(self):
        self.db = MongoService()
        self.core = CoreService()
        self.aggregator = AggregatorService()
        self.scheduler = SystemSchedulerService()
        self.gui = GuiService()
        self.execution = ExecutionService()
        self.static_correlator = StaticCorrelatorService()
        self.reports = ReportsService()

        self.axonius_services = [self.db, self.core, self.aggregator, self.scheduler, self.gui, self.execution,
                                 self.static_correlator, self.reports]

    @classmethod
    def get_is_network_exists(cls):
        return cls._NETWORK_NAME in subprocess.check_output(['docker', 'network', 'ls', '--filter',
                                                             f'name={cls._NETWORK_NAME}']).decode('utf-8')

    @classmethod
    def create_network(cls):
        if cls.get_is_network_exists():
            return
        subprocess.check_call(['docker', 'network', 'create', cls._NETWORK_NAME], stdout=subprocess.PIPE)

    @classmethod
    def delete_network(cls):
        if not cls.get_is_network_exists():
            return
        subprocess.check_call(['docker', 'network', 'rm', cls._NETWORK_NAME], stdout=subprocess.PIPE)

    def stop(self, should_delete, remove_image=False):
        # Not critical but lets stop in reverse order
        async_items = []
        for service in self.axonius_services[::-1]:
            current = iter(service.stop_async(should_delete=should_delete, remove_image=remove_image))
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

    def start_and_wait(self, mode='', allow_restart=False, rebuild=False, hard=False, skip=False, show_print=True):
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
            service.start(mode=mode, allow_restart=allow_restart, hard=hard, show_print=show_print)

        # wait for all
        for service in self.axonius_services:
            service.wait_for_service()

    def get_devices_db(self):
        return self.db.get_entity_db(EntityType.Devices)

    def get_users_db(self):
        return self.db.get_entity_db(EntityType.Users)

    def insert_device(self, device_data):
        self.get_devices_db().insert_one(device_data)

    def get_devices_with_condition(self, cond):
        cursor = self.get_devices_db().find(cond)
        return list(cursor)

    def get_users_with_condition(self, cond):
        cursor = self.get_users_db().find(cond)
        return list(cursor)

    def get_device_by_id(self, adapter_name, device_id):
        cond = {'adapters.data.id': device_id, 'adapters.plugin_unique_name': adapter_name}
        return self.get_devices_with_condition(cond)

    def get_device_network_interfaces(self, adapter_name, device_id):
        device = self.get_device_by_id(adapter_name, device_id)
        adapter_device = next(adapter_device for adapter_device in device[0]['adapters'] if
                              adapter_device[PLUGIN_UNIQUE_NAME] == adapter_name)
        return adapter_device['data'][NETWORK_INTERFACES_FIELD]

    def assert_device_aggregated(self, adapter, client_details, max_tries=30):
        self.aggregator.query_devices(adapter_id=adapter.unique_name)  # send trigger to agg to refresh devices
        for client_id, some_device_id in client_details:
            devices = self.get_device_by_id(adapter.unique_name, some_device_id)
            assert len(devices) == 1

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
    def _get_docker_service(type_name, name):
        module = importlib.import_module(f"services.{type_name}.{name.lower()}_service")
        return getattr(module, ' '.join(name.lower().split('_')).title().replace(' ', '') + 'Service')()

    @classmethod
    def get_plugin(cls, name):
        return cls._get_docker_service('plugins', name)

    @classmethod
    def get_adapter(cls, name):
        return cls._get_docker_service('adapters', name)

    def start_plugins(self, adapter_names, plugin_names, mode='', allow_restart=False, rebuild=False, hard=False,
                      skip=False, show_print=True, exclude_restart=None):
        plugins = [self.get_adapter(name) for name in adapter_names] + [self.get_plugin(name) for name in plugin_names]
        if exclude_restart is None:
            exclude_restart = []
        if rebuild:
            for plugin in plugins:
                plugin.remove_image()
        if allow_restart:
            for plugin in plugins:
                if self.get_plugin_short_name(plugin) in exclude_restart and plugin.get_is_container_up():
                    continue
                plugin.remove_container()
        for plugin in plugins:
            plugin.take_process_ownership()
            if plugin.get_is_container_up():
                if skip:
                    continue
                elif self.get_plugin_short_name(plugin) in exclude_restart:
                    print(f'Ignoring - {self.get_plugin_short_name(plugin)}')
                    continue
            plugin.start(mode, allow_restart=allow_restart, hard=hard, show_print=show_print)
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

    def stop_plugins(self, adapter_names, plugin_names, should_delete, remove_image=False, exclude_restart=None):
        plugins = [self.get_adapter(name) for name in adapter_names] + [self.get_plugin(name) for name in plugin_names]
        if exclude_restart is None:
            exclude_restart = []

        async_items = []
        for plugin in plugins:
            if self.get_plugin_short_name(plugin) in exclude_restart and plugin.get_is_container_up():
                continue
            plugin.take_process_ownership()
            current = iter(plugin.stop_async(should_delete=should_delete, remove_image=remove_image))
            next(current)  # actual stop call
            async_items.append(current)
        # stop_async is a generator that yields just after the first exec, that is why we run next(current) before
        # adding it to async_items; and after we go over all services, we need to complete the rest of the function
        # using next (in the 'for _ in async_item')
        for async_item in async_items:
            for _ in async_item:
                pass

    def remove_plugin_containers(self, adapter_names, plugin_names, exclude_restart=None):
        plugins = [self.get_adapter(name) for name in adapter_names] + [self.get_plugin(name) for name in plugin_names]

        if exclude_restart is None:
            exclude_restart = []
        for plugin in plugins:
            if self.get_plugin_short_name(plugin) in exclude_restart and plugin.get_is_container_up():
                continue
            plugin.remove_container()

    def _get_all_docker_services(self, type_name, obj):
        folder = os.path.dirname(inspect.getfile(obj))
        regex = os.path.join(folder, '*_service.py')
        return_list = []

        for path in glob.glob(regex):
            module_name = os.path.basename(path)[:-3]
            if module_name == '__init__':
                continue
            module = importlib.import_module(f'services.{type_name}.{module_name}')
            variable = getattr(module, ' '.join(module_name.split('_')).title().replace(' ', ''))
            not_internal = True
            for service in self.axonius_services:
                if isinstance(service, variable):
                    not_internal = False
                    break
            if not_internal:
                return_list.append((module_name[:-len('_service')], variable))
        return return_list

    def get_all_plugins(self):
        return self._get_all_docker_services('plugins', plugins)

    def get_all_adapters(self):
        return self._get_all_docker_services('adapters', adapters)

    def pull_base_image(self, repull=False, show_print=True):
        base_image = 'axonius/axonius-base-image'
        base_image_exists = base_image in subprocess.check_output(['docker', 'images', base_image]).decode('utf-8')
        if base_image_exists and not repull:
            if show_print:
                print('Base image already exists - skipping pull step')
            return base_image
        runner = ParallelRunner()
        runner.append_single('axonius-base-image', ['docker', 'pull', base_image])
        assert runner.wait_for_all() == 0
        return base_image

    def build_libs(self, rebuild=False, show_print=True):
        image_name = 'axonius/axonius-libs'
        output = subprocess.check_output(['docker', 'images', image_name]).decode('utf-8')
        image_exists = image_name in output
        if image_exists:
            if rebuild:
                subprocess.call(['docker', 'rmi', image_name, '--force'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                if show_print:
                    print('Image axonius-libs already built - skipping build step')
                return image_name
        runner = ParallelRunner()
        runner.append_single('axonius-libs', ['docker', 'build', '.', '-t', image_name],
                             cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'axonius-libs')))
        assert runner.wait_for_all() == 0
        return image_name

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
        images = []
        if async and len(to_build) > 1:
            runner = ParallelRunner()
            for service in to_build:
                images.append(service.image)
                if service.get_image_exists():
                    continue
                service.build(mode, runner)
                time.sleep(1)  # We are getting resource busy. we suspect this is due parallel build storm
            assert runner.wait_for_all() == 0
        else:
            for service in to_build:
                if service.get_image_exists():
                    continue
                service.build(mode)
                images.append(service.image)
        return images

    @staticmethod
    def get_plugin_short_name(plugin_obj):
        short_name = os.path.basename(inspect.getfile(plugin_obj.__class__))
        assert short_name.endswith('_service.py')
        return short_name[:-len('_service.py')]
