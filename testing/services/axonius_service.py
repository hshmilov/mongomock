import glob
import importlib
import inspect
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timedelta

from axonius.consts.plugin_consts import (AXONIUS_NETWORK,
                                          CONFIGURABLE_CONFIGS_COLLECTION,
                                          ENCRYPTION_KEY_FILENAME,
                                          PLUGIN_UNIQUE_NAME,
                                          AXONIOUS_SETTINGS_DIR_NAME, SYSTEM_SETTINGS,
                                          WEAVE_NETWORK,
                                          WEAVE_PATH)
from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD
from axonius.plugin_base import EntityType
from services import adapters, plugins
from services.axon_service import TimeoutException
from services.docker_service import is_weave_up
from services.plugins.aggregator_service import AggregatorService
from services.plugins.core_service import CoreService
from services.plugins.execution_service import ExecutionService
from services.plugins.gui_service import GuiService
from services.plugins.mongo_service import MongoService
from services.plugins.reports_service import ReportsService
from services.plugins.static_correlator_service import StaticCorrelatorService
from services.plugins.static_users_correlator_service import \
    StaticUsersCorrelatorService
from services.plugins.system_scheduler_service import SystemSchedulerService
from test_helpers.parallel_runner import ParallelRunner
from test_helpers.utils import try_until_not_thrown

BLACKLIST_LABEL = 'do_not_execute'


def get_service():
    return AxoniusService()


class AxoniusService:
    _NETWORK_NAME = WEAVE_NETWORK if 'linux' in sys.platform.lower() else AXONIUS_NETWORK

    def __init__(self):
        self.db = MongoService()
        self.core = CoreService()
        self.aggregator = AggregatorService()
        self.scheduler = SystemSchedulerService()
        self.gui = GuiService()
        self.execution = ExecutionService()
        self.static_correlator = StaticCorrelatorService()
        self.static_users_correlator = StaticUsersCorrelatorService()
        self.reports = ReportsService()

        self.axonius_services = [self.db, self.core, self.aggregator, self.scheduler, self.gui, self.execution,
                                 self.static_correlator, self.static_users_correlator, self.reports]

    @classmethod
    def get_is_network_exists(cls):
        if cls._NETWORK_NAME == WEAVE_NETWORK:
            return is_weave_up()
        else:
            return cls._NETWORK_NAME in subprocess.check_output(['docker', 'network', 'ls', '--filter',
                                                                 f'name={cls._NETWORK_NAME}']).decode('utf-8')

    @classmethod
    def create_network(cls):
        if cls.get_is_network_exists():
            return

        if 'linux' in sys.platform.lower():
            # Getting network encryption key.
            key_file_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', AXONIOUS_SETTINGS_DIR_NAME,
                             ENCRYPTION_KEY_FILENAME))
            if os.path.exists(key_file_path):
                with open(key_file_path, 'r') as encryption_key_file:
                    encryption_key = encryption_key_file.read()
            else:
                # Creating a new one if it doesn't exist yet.
                encryption_key = subprocess.check_output(
                    'dd if=/dev/random bs=1 count=32 2>/dev/null | base64 -w 0 | rev | cut -b 2- | rev',
                    shell=True).decode("utf-8")
                os.makedirs(
                    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', AXONIOUS_SETTINGS_DIR_NAME)),
                    exist_ok=True)
                with open(key_file_path, 'w') as encryption_key_file:
                    encryption_key_file.write(encryption_key)

            subprocess.check_call(
                [WEAVE_PATH, 'launch', '--dns-domain="axonius.local"', '--password', encryption_key],
                stdout=subprocess.PIPE)
        else:
            subprocess.check_call(['docker', 'network', 'create', '--subnet=171.17.0.0/16', cls._NETWORK_NAME],
                                  stdout=subprocess.PIPE)

    @classmethod
    def delete_network(cls):
        if not cls.get_is_network_exists():
            return

        print('Deleting docker network')
        if 'linux' in sys.platform.lower() and is_weave_up():
            subprocess.check_call([WEAVE_PATH, 'reset'], stdout=subprocess.PIPE)
        else:
            subprocess.check_call(['docker', 'network', 'rm', cls._NETWORK_NAME], stdout=subprocess.PIPE)

    def stop(self, **kwargs):
        # Not critical but lets stop in reverse order
        async_items = []
        for service in self.axonius_services[::-1]:
            current = iter(service.stop_async(**kwargs))
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

    def start_and_wait(self, mode='', allow_restart=False, rebuild=False, hard=False, skip=False, show_print=True,
                       expose_db=False):

        def _start_service(service_to_start):
            if skip and service_to_start.get_is_container_up():
                return
            if expose_db and service_to_start is self.db:
                service_to_start.start(mode=mode, allow_restart=allow_restart, rebuild=rebuild,
                                       hard=hard, show_print=show_print, expose_port=True)
                return
            service_to_start.start(mode=mode, allow_restart=allow_restart, rebuild=rebuild, hard=hard,
                                   show_print=show_print)

        if allow_restart:
            for service in self.axonius_services:
                service.remove_container()

        # Start in parallel
        services_to_start = list(self.axonius_services)

        mongo_service = next((x for x in services_to_start if x.container_name == 'mongo'), None)
        if mongo_service:
            # if mongo is also restarted, we can't restart anything else before it finishes
            _start_service(mongo_service)
            mongo_service.wait_for_service()
            services_to_start.remove(mongo_service)

        core_service = next((x for x in services_to_start if x.container_name == 'core'), None)
        if core_service:
            # if core is also restarted, we can't restart anything else before it finishes
            _start_service(core_service)
            core_service.wait_for_service()
            services_to_start.remove(core_service)

        for service in services_to_start:
            _start_service(service)

        # wait for all
        for service in services_to_start:
            service.wait_for_service()

    def blacklist_device(self, plugin_unique_name, device_id):
        device_to_blacklist = self.get_device_by_id(plugin_unique_name, device_id)
        assert len(device_to_blacklist) == 1
        device_to_blacklist = device_to_blacklist[0]
        result = self.gui.add_labels_to_device({
            'entities': {
                'ids': [device_to_blacklist['internal_axon_id']], 'include': True
            }, 'labels': [BLACKLIST_LABEL]
        })
        assert result.status_code == 200, f'Failed adding label. reason: ' \
                                          f'{str(result.status_code)}, {str(result.content)}'

    def get_devices_db(self):
        return self.db.get_entity_db(EntityType.Devices)

    def get_devices_db_view(self):
        return self.db.get_entity_db_view(EntityType.Devices)

    def get_users_db(self):
        return self.db.get_entity_db(EntityType.Users)

    def get_users_db_view(self):
        return self.db.get_entity_db_view(EntityType.Users)

    def get_reports_db(self):
        return self.db.get_collection(self.reports.unique_name, 'reports')

    def get_notifications_db(self):
        return self.db.get_collection(self.core.unique_name, 'notifications')

    def get_system_users_db(self):
        return self.db.gui_users_collection()

    def insert_device(self, device_data):
        self.get_devices_db().insert_one(device_data)
        self.aggregator.rebuild_views([device_data['internal_axon_id']])

    def delete_device_by_query(self, query):
        self.get_devices_db().delete_one(query)
        self.aggregator.rebuild_views()

    def insert_user(self, user_data):
        self.get_users_db().insert_one(user_data)
        self.aggregator.rebuild_views([user_data['internal_axon_id']])

    def insert_report(self, report_data):
        self.get_reports_db().insert_one(report_data)

    def db_find(self, db_name, collection_name, cond):
        return list(self.db.get_collection(db_name, collection_name).find(cond))

    def get_devices_with_condition(self, cond):
        cursor = self.get_devices_db().find(cond)
        return list(cursor)

    def get_devices_view_with_condition(self, cond):
        cursor = self.get_devices_db_view().find(cond)
        return list(cursor)

    def get_users_with_condition(self, cond):
        cursor = self.get_users_db().find(cond)
        return list(cursor)

    def get_users_view_with_condition(self, cond):
        cursor = self.get_users_db_view().find(cond)
        return list(cursor)

    def get_device_by_id(self, adapter_name, device_id):
        cond = {
            'adapters': {
                "$elemMatch": {
                    'data.id': device_id,
                    PLUGIN_UNIQUE_NAME: adapter_name
                }
            }
        }
        return self.get_devices_with_condition(cond)

    def get_device_view_by_id(self, adapter_name, device_id):
        cond = {
            'specific_data': {
                "$elemMatch": {
                    'data.id': device_id,
                    PLUGIN_UNIQUE_NAME: adapter_name
                }
            }
        }
        return self.get_devices_view_with_condition(cond)

    def get_user_by_id(self, adapter_name, user_id):
        cond = {
            'adapters': {
                "$elemMatch": {
                    'data.id': user_id,
                    PLUGIN_UNIQUE_NAME: adapter_name
                }
            }
        }
        return self.get_users_with_condition(cond)

    def get_user_view_by_id(self, adapter_name, user_id):
        cond = {
            'specific_data': {
                "$elemMatch": {
                    'data.id': user_id,
                    PLUGIN_UNIQUE_NAME: adapter_name
                }
            }
        }
        return self.get_users_view_with_condition(cond)

    def get_device_network_interfaces(self, adapter_name, device_id):
        device = self.get_device_by_id(adapter_name, device_id)
        adapter_device = next(adapter_device for adapter_device in device[0]['adapters'] if
                              adapter_device[PLUGIN_UNIQUE_NAME] == adapter_name)
        return adapter_device['data'][NETWORK_INTERFACES_FIELD]

    def assert_device_aggregated(self, adapter, client_details):
        # triggers a query and checks for the existence of a certain device
        self.aggregator.query_devices(adapter_id=adapter.unique_name)  # send trigger to agg to refresh devices
        for _, some_device_id in client_details:
            self.assert_device_in_db(adapter.unique_name, some_device_id)

    def assert_device_in_db(self, plugin_unique_name, some_device_id):
        devices = self.get_device_by_id(plugin_unique_name, some_device_id)
        assert len(devices) == 1
        devices = self.get_device_view_by_id(plugin_unique_name, some_device_id)
        assert len(devices) == 1

    def assert_user_aggregated(self, adapter, client_details):
        # triggers a query and checks for the existence of a certain user
        self.aggregator.query_devices(adapter_id=adapter.unique_name)  # send trigger to agg to refresh devices
        for _, some_device_id in client_details:
            self.assert_user_in_db(adapter.unique_name, some_device_id)

    def assert_user_in_db(self, plugin_unique_name, some_device_id):
        users = self.get_user_by_id(plugin_unique_name, some_device_id)
        assert len(users) == 1
        users = self.get_user_view_by_id(plugin_unique_name, some_device_id)
        assert len(users) == 1

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

        # let's wait until all other plugins are up as well
        # this is not the best solution but at least it works
        time.sleep(30)

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
                      skip=False, show_print=True, env_vars=None):
        plugins = [self.get_adapter(name) for name in adapter_names] + [self.get_plugin(name) for name in plugin_names]

        if allow_restart:
            for plugin in plugins:
                plugin.remove_container()
        for plugin in plugins:
            plugin.take_process_ownership()
            if plugin.get_is_container_up():
                if skip:
                    continue
            plugin.start(mode, allow_restart=allow_restart, rebuild=rebuild,
                         hard=hard, show_print=show_print, env_vars=env_vars)
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

    def stop_plugins(self, adapter_names, plugin_names, **kwargs):
        plugins = [self.get_adapter(name) for name in adapter_names] + [self.get_plugin(name) for name in plugin_names]

        async_items = []
        for plugin in plugins:
            plugin.take_process_ownership()
            current = iter(plugin.stop_async(**kwargs))
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

    def _pull_image(self, image_name, repull=False, show_print=True):
        image_exists = image_name in subprocess.check_output(['docker', 'images', image_name]).decode('utf-8')
        if image_exists and not repull:
            if show_print:
                print(f'Image {image_name} already exists - skipping pull step')
            return image_name
        runner = ParallelRunner()
        runner.append_single('axonius-image-pull', ['docker', 'pull', image_name])
        assert runner.wait_for_all() == 0
        return image_name

    def pull_weave_images(self, repull=False, show_print=True):
        weave_images = ['weaveworks/weavedb', 'weaveworks/weaveexec:2.5.0', 'weaveworks/weave:2.5.0']
        for current_weave_image in weave_images:
            self._pull_image(current_weave_image, repull, show_print)
        return weave_images

    def pull_curl_image(self, repull=False, show_print=True):
        curl_image = 'appropriate/curl'
        return self._pull_image(curl_image, repull, show_print)

    def pull_tunnler(self, repull=False, show_print=True):
        # Tunnler is a tunnel to host:22 for ssh and scp from master to nodes.
        tunnler_image = 'alpine/socat'
        return self._pull_image(tunnler_image, repull, show_print)

    def pull_base_image(self, repull=False, show_print=True):
        base_image = 'axonius/axonius-base-image'
        return self._pull_image(base_image, repull, show_print)

    def build_libs(self, rebuild=False, show_print=True):
        image_name = 'axonius/axonius-libs'
        output = subprocess.check_output(['docker', 'images', image_name]).decode('utf-8')
        image_exists = image_name in output
        if image_exists and not rebuild:
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
        if hard:
            for service in to_build:
                service.remove_volume()
        images = []
        if async and len(to_build) > 1:
            runner = ParallelRunner()
            for service in to_build:
                images.append(service.image)
                if not rebuild and service.get_image_exists():
                    continue
                service.build(mode, runner)
                time.sleep(1)  # We are getting resource busy. we suspect this is due parallel build storm
            assert runner.wait_for_all() == 0
        else:
            for service in to_build:
                images.append(service.image)
                if not rebuild and service.get_image_exists():
                    continue
                service.build(mode)
        return images

    @staticmethod
    def get_plugin_short_name(plugin_obj):
        short_name = os.path.basename(inspect.getfile(plugin_obj.__class__))
        assert short_name.endswith('_service.py')
        return short_name[:-len('_service.py')]

    def set_system_settings(self, settings_dict):
        settings = self.db.get_collection(self.gui.unique_name, CONFIGURABLE_CONFIGS_COLLECTION)
        settings.update_one(filter={"config_name": "GuiService"},
                            update={"$set": {f"config.{SYSTEM_SETTINGS}": settings_dict}})

    def add_view(self, view_params):
        views = self.db.get_collection(self.gui.unique_name, 'device_views')
        views.insert_one(view_params)

    def set_research_rate(self, rate):
        settings = self.db.get_collection(self.scheduler.unique_name, CONFIGURABLE_CONFIGS_COLLECTION)
        settings.update_one(filter={"config_name": "SystemSchedulerService"},
                            update={"$set": {"config.system_research_rate": rate}})
