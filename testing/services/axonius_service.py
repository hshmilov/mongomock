import glob
import importlib
import inspect
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from multiprocessing.pool import ThreadPool

import pytest

from axonius.consts.plugin_consts import (CONFIGURABLE_CONFIGS_COLLECTION,
                                          PLUGIN_UNIQUE_NAME, SYSTEM_SETTINGS, GUI_SYSTEM_CONFIG_COLLECTION)
from axonius.consts.system_consts import (AXONIUS_DNS_SUFFIX, AXONIUS_NETWORK,
                                          NODE_MARKER_PATH,
                                          WEAVE_PATH, DOCKERHUB_USER, WEAVE_VERSION, DOCKERHUB_URL, USING_WEAVE_PATH)
from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD
from axonius.plugin_base import EntityType
from scripts.instances.network_utils import (get_encryption_key,
                                             restore_master_connection, get_weave_subnet_ip_range,
                                             get_docker_subnet_ip_range, DOCKER_BRIDGE_INTERFACE_NAME)
from services import adapters, plugins, standalone_services
from services.axon_service import TimeoutException
from services.plugin_service import AdapterService, PluginService
from services.plugins.aggregator_service import AggregatorService
from services.plugins.core_service import CoreService
from services.plugins.execution_service import ExecutionService
from services.plugins.gui_service import GuiService
from services.plugins.heavy_lifting_service import HeavyLiftingService
from services.plugins.mongo_service import MongoService
from services.plugins.instance_control_service import InstanceControlService
from services.plugins.reports_service import ReportsService
from services.plugins.static_correlator_service import StaticCorrelatorService
from services.plugins.static_users_correlator_service import StaticUsersCorrelatorService
from services.plugins.system_scheduler_service import SystemSchedulerService
from services.plugins.master_proxy_service import MasterProxyService
from services.weave_service import is_weave_up, is_using_weave
from test_helpers.parallel_runner import ParallelRunner
from test_helpers.utils import try_until_not_thrown

DNS_REGISTER_POOL_SIZE = 5


def get_service():
    return AxoniusService()


# pylint: disable=too-many-instance-attributes

class AxoniusService:
    _DOCKER_NETWORK_NAME = AXONIUS_NETWORK

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
        self.heavy_lifting = HeavyLiftingService()
        self.instance_control = InstanceControlService()
        self.master_proxy = MasterProxyService()
        self.axonius_services = [self.db,
                                 self.core,
                                 self.aggregator,
                                 self.scheduler,
                                 self.gui,
                                 self.execution,
                                 self.static_correlator,
                                 self.static_users_correlator,
                                 self.heavy_lifting,
                                 self.reports,
                                 self.master_proxy,
                                 ]

        # No instance control on windows
        if 'linux' in sys.platform.lower():
            self.axonius_services.append(self.instance_control)

    @classmethod
    def get_is_docker_network_exists(cls):
        return cls._DOCKER_NETWORK_NAME in subprocess.check_output(['docker', 'network', 'ls', '--filter',
                                                                    f'name={cls._DOCKER_NETWORK_NAME}']).decode('utf-8')

    @classmethod
    def create_network(cls):
        if not cls.get_is_docker_network_exists():
            print(f'Creating regular axonius network')
            docker_subnet_ip_range = get_docker_subnet_ip_range()
            subprocess.check_call(
                ['docker', 'network', 'create', f'--subnet={docker_subnet_ip_range}',
                 '--opt', f'com.docker.network.bridge.name={DOCKER_BRIDGE_INTERFACE_NAME}',
                 cls._DOCKER_NETWORK_NAME],
                stdout=subprocess.PIPE)
        if not is_weave_up() and 'linux' in sys.platform.lower():
            weave_subnet_ip_range = get_weave_subnet_ip_range()
            # Getting network encryption key.
            if NODE_MARKER_PATH.is_file():
                print(f'Running on node. Refreshing master connection')
                restore_master_connection()
            else:
                print(f'Running on master')
                AxoniusService.create_weave_network(weave_subnet_ip_range)
        if NODE_MARKER_PATH.is_file():
            # now that we know we are using weave, create a "using weave" marker file
            if not is_using_weave():
                USING_WEAVE_PATH.touch()

    @classmethod
    def delete_network(cls):
        if 'linux' in sys.platform.lower() and is_weave_up():
            print('Deleting weave network')
            subprocess.check_call([WEAVE_PATH, 'reset'], stdout=subprocess.PIPE)
        if cls.get_is_docker_network_exists():
            print('Deleting docker network')
            subprocess.check_call(['docker', 'network', 'rm', cls._DOCKER_NETWORK_NAME], stdout=subprocess.PIPE)

    @staticmethod
    def create_weave_network(subnet_ip_range: str):
        """
        Creating a new weave network using weave script
        :param subnet_ip_range: weave network subnet
        :return: None
        """
        encryption_key = get_encryption_key()
        print(f'Creating weave network')
        # this command should launch weave network
        # with our dns suffix, ip allocation range and encryption password using weave shell script.
        env = {'DOCKER_BRIDGE': DOCKER_BRIDGE_INTERFACE_NAME}
        weave_launch_command = [WEAVE_PATH, 'launch',
                                f'--dns-domain="{AXONIUS_DNS_SUFFIX}"', '--ipalloc-range', subnet_ip_range,
                                '--password',
                                encryption_key.strip()]
        subprocess.check_call(weave_launch_command, env=env)

    @staticmethod
    def register_service(service: PluginService):
        """
        Register service dns records into an existing weave network
        :param service: service to register
        :return:
        """
        if service.get_is_container_up() and service.should_register_unique_dns:
            print(f'Register {service.service_name}')
            service.register_unique_dns()

    def recover_weave_network(self, adapter_names: list, plugin_names: list, standalone_services_names: list):
        """
        This function should handle the weave 'zombie' state.
        On this state usually we cant run new docker containers - they got stuck on creation.
        This happens because of an unknown bug on weave proxy
        which cause some containers running without weave network interface ('ethwe')
        And thats why weavewait gets stuck and crash sometimes
        (weavewait should wait for 'ethwe' interface and then run the docker entry point)
        Ive found out that the best solution is to 'reload' weave network -
        without shutting down or removing our containers.
        for doing this we should:
        1. Stop weave proxy (weaver) by running 'weave stop'
        2. Relaunching weave
            on this step weave will attach each running container and add its interface on weave network
        3. If we are running on a node - reconnect to the master.
        4. Re register containers dns records
        :param adapter_names: running adapter names
        :param plugin_names: running plugin names
        :param standalone_services_names: running standalone services
        :return: None
        """
        print('Stopping weave network')
        subprocess.check_call(f'{WEAVE_PATH} stop'.split())

        # this should relaunch weave and connect to master if its a node
        self.create_network()

        print('Registering dns records')
        all_services_to_start = [self.get_adapter(name) for name in sorted(adapter_names)] + \
                                [self.get_plugin(name) for name in sorted(plugin_names)] + \
                                [self.get_standalone_service(name) for name in sorted(standalone_services_names)]
        with ThreadPool(DNS_REGISTER_POOL_SIZE) as pool:
            pool.map(self.register_service, all_services_to_start)

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

    def _process_internal_service_white_list(self, internal_service_white_list):
        if internal_service_white_list is not None:
            services_to_start = list(
                [service for service in self.axonius_services if service.service_name in internal_service_white_list])
        else:
            services_to_start = list(self.axonius_services)

        return services_to_start

    def start_and_wait(
            self,
            mode='',
            allow_restart=False,
            rebuild=False,
            hard=False,
            skip=False,
            show_print=True,
            expose_db=False,
            env_vars=None,
            internal_service_white_list=None,
            system_config=None
    ):
        def _start_service(service_to_start):
            service_to_start.set_system_config(system_config)
            if skip and service_to_start.get_is_container_up():
                return
            if expose_db and service_to_start is self.db:
                service_to_start.start(mode=mode, allow_restart=allow_restart, rebuild=rebuild,
                                       hard=hard, show_print=show_print, expose_port=True,
                                       docker_internal_env_vars=env_vars)
                return
            service_to_start.start(mode=mode, allow_restart=allow_restart, rebuild=rebuild, hard=hard,
                                   show_print=show_print, docker_internal_env_vars=env_vars)

        self.create_network()

        if allow_restart:
            for service in self.axonius_services:
                service.remove_container()

        # Start in parallel
        services_to_start = self._process_internal_service_white_list(internal_service_white_list)

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
            if service.should_register_unique_dns:
                service.register_unique_dns()

    def get_devices_db(self):
        return self.db.get_entity_db(EntityType.Devices)

    def get_users_db(self):
        return self.db.get_entity_db(EntityType.Users)

    def get_enforcements_db(self):
        return self.db.get_collection(self.reports.unique_name, 'reports')

    def get_actions_db(self):
        return self.db.get_collection(self.reports.unique_name, 'saved_actions')

    def get_tasks_db(self):
        return self.db.get_collection(self.reports.unique_name, 'triggerable_history')

    def get_tasks_running_id_db(self):
        return self.db.get_collection(self.reports.unique_name, 'running_id')

    def get_notifications_db(self):
        return self.db.get_collection(self.core.unique_name, 'notifications')

    def get_system_users_db(self):
        return self.db.gui_users_collection()

    def get_aggregator_devices_fields_db(self):
        return self.db.get_collection(self.aggregator.unique_name, 'devices_fields')

    def get_users_preferences_db(self):
        return self.db.gui_users_preferences_collection()

    def get_roles_db(self):
        return self.db.gui_roles_collection()

    def get_reports_config_db(self):
        return self.db.gui_reports_config_collection()

    def get_dashboard_spaces_db(self):
        return self.db.gui_dashboard_spaces_collection()

    def get_dashboard_db(self):
        return self.db.gui_dashboard_collection()

    def insert_device(self, device_data):
        self.get_devices_db().insert_one(device_data)

    def delete_device_by_query(self, query):
        self.get_devices_db().delete_one(query)

    def insert_user(self, user_data):
        self.get_users_db().insert_one(user_data)

    def insert_report(self, report_data):
        self.get_enforcements_db().insert_one(report_data)

    def db_find(self, db_name, collection_name, cond):
        return list(self.db.get_collection(db_name, collection_name).find(cond))

    def get_devices_with_condition(self, cond):
        cursor = self.get_devices_db().find(cond)
        return list(cursor)

    def get_users_with_condition(self, cond):
        cursor = self.get_users_db().find(cond)
        return list(cursor)

    def get_device_by_id(self, adapter_name, device_id):
        cond = {
            'adapters': {
                '$elemMatch': {
                    'data.id': device_id,
                    PLUGIN_UNIQUE_NAME: adapter_name
                }
            }
        }
        return self.get_devices_with_condition(cond)

    def get_devices_by_adapter_name(self, adapter_name):
        cond = {
            'adapters': {
                '$elemMatch': {
                    PLUGIN_UNIQUE_NAME: adapter_name
                }
            }
        }
        return self.get_devices_with_condition(cond)

    def get_user_by_id(self, adapter_name, user_id):
        cond = {
            'adapters': {
                '$elemMatch': {
                    'data.id': user_id,
                    PLUGIN_UNIQUE_NAME: adapter_name
                }
            }
        }
        return self.get_users_with_condition(cond)

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
        if len(devices) != 1:
            device_ids = [device.get('adapters', [{}])[0].get('data', {}).get('id')
                          for device in self.get_devices_by_adapter_name(plugin_unique_name)]
            pytest.fail('{0} exists more then once or not in {1}'.format(some_device_id, device_ids))
        devices = self.get_device_by_id(plugin_unique_name, some_device_id)
        assert len(devices) == 1

    def assert_user_aggregated(self, adapter, client_details):
        # triggers a query and checks for the existence of a certain user
        self.aggregator.query_devices(adapter_id=adapter.unique_name)  # send trigger to agg to refresh devices
        for _, some_device_id in client_details:
            self.assert_user_in_db(adapter.unique_name, some_device_id)

    def assert_user_in_db(self, plugin_unique_name, some_device_id):
        users = self.get_user_by_id(plugin_unique_name, some_device_id)
        assert len(users) == 1

    def restart_plugin(self, plugin):
        """
        :param plugin: plugin to restart
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
            assert datetime.now() - current_time < timedelta(seconds=120)
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
        module = importlib.import_module(f'services.{type_name}.{name.lower()}_service')
        return getattr(module, ' '.join(name.lower().split('_')).title().replace(' ', '') + 'Service')()

    @classmethod
    def get_plugin(cls, name) -> PluginService:
        return cls._get_docker_service('plugins', name)

    @classmethod
    def get_adapter(cls, name) -> AdapterService:
        return cls._get_docker_service('adapters', name)

    @classmethod
    def get_standalone_service(cls, name):
        return cls._get_docker_service('standalone_services', name)

    def register_unique_dns(self, adapter_names,
                            plugin_names,
                            standalone_services_names,
                            system_base=False,
                            system_config=None):
        all_services_to_start = [self.get_adapter(name) for name in sorted(adapter_names)] + \
                                [self.get_plugin(name) for name in sorted(plugin_names)] + \
                                [self.get_standalone_service(name) for name in sorted(standalone_services_names)]

        if system_base:
            all_services_to_start += self.axonius_services

        for service in all_services_to_start:
            service.set_system_config(system_config)
            service.take_process_ownership()
            if service.get_is_container_up() and service.should_register_unique_dns:
                service.register_unique_dns()

    def start_plugins(
            self,
            adapter_names,
            plugin_names,
            standalone_services_names,
            mode='',
            allow_restart=False,
            rebuild=False,
            hard=False,
            skip=False,
            show_print=True,
            env_vars=None,
            system_config=None,
    ):
        all_services_to_start = [self.get_adapter(name) for name in sorted(adapter_names)] + \
                                [self.get_plugin(name) for name in sorted(plugin_names)] + \
                                [self.get_standalone_service(name) for name in sorted(standalone_services_names)]

        if allow_restart:
            for service in all_services_to_start:
                service.remove_container()

        def start_and_wait_for_service(service):
            """
            Returns the problematic service if there's an error. Otherwise returns None
            """
            try:
                service.set_system_config(system_config)
                service.take_process_ownership()
                if service.get_is_container_up():
                    if skip:
                        return None
                service.start(mode, allow_restart=allow_restart, rebuild=rebuild,
                              hard=hard, show_print=show_print, docker_internal_env_vars=env_vars)
                service.wait_for_service(120)
                if service.should_register_unique_dns:
                    service.register_unique_dns()
                return None
            except Exception as e:
                print(e)
                return service

        with ThreadPool(5) as pool:
            errors = [x for x in pool.map(start_and_wait_for_service, all_services_to_start) if x]

        if len(errors) > 0:
            # plugins contains failed ones and should be removed to make sure the state is stable for next time.
            try:
                for plugin in errors:
                    print(f'Logs of {plugin.container_name}:')
                    os.system(f'docker logs {plugin.container_name}')
            except Exception as e:
                print(f'Failed getting logs, {e}')
            for service in errors:
                service.stop(should_delete=True)
            raise TimeoutException(repr([plugin.container_name for plugin in errors]))

    def stop_plugins(self, adapter_names, plugin_names, standalone_services_names, **kwargs):
        all_services_to_stop = [self.get_adapter(name) for name in adapter_names] + \
                               [self.get_plugin(name) for name in plugin_names] + \
                               [self.get_standalone_service(name) for name in standalone_services_names]

        async_items = []
        for plugin in all_services_to_stop:
            plugin.take_process_ownership()
            current = iter(plugin.stop_async(**kwargs))
            next(current)  # actual stop call
            async_items.append(current)

            # We do not want more than 30 containers getting down at the same time since this can cause docker issues.
            if len(async_items) == 30:
                for async_item in async_items:
                    for _ in async_item:
                        pass

                async_items = []
        # stop_async is a generator that yields just after the first exec, that is why we run next(current) before
        # adding it to async_items; and after we go over all services, we need to complete the rest of the function
        # using next (in the 'for _ in async_item')
        for async_item in async_items:
            for _ in async_item:
                pass

    def remove_plugin_containers(self, adapter_names, plugin_names):
        all_services_containers_to_remove = [self.get_adapter(name) for name in adapter_names] + [self.get_plugin(name)
                                                                                                  for name in
                                                                                                  plugin_names]

        for plugin in all_services_containers_to_remove:
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

    def get_all_standalone_services(self):
        return self._get_all_docker_services('standalone_services', standalone_services)

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
        weave_images = [f'{DOCKERHUB_USER}/weavedb', f'{DOCKERHUB_USER}/weaveexec:{WEAVE_VERSION}',
                        f'{DOCKERHUB_USER}/weave:{WEAVE_VERSION}']
        for current_weave_image in weave_images:
            self._pull_image(current_weave_image, repull, show_print)
        return weave_images

    def pull_curl_image(self, repull=False, show_print=True):

        curl_image = f'{DOCKERHUB_URL}appropriate/curl'
        return self._pull_image(curl_image, repull, show_print)

    def pull_tunneler(self, repull=False, show_print=True):
        # tunneler is a tunnel to host:22 for ssh and scp from master to nodes.
        tunneler_image = f'{DOCKERHUB_URL}alpine/socat'
        return self._pull_image(tunneler_image, repull, show_print)

    def pull_base_image(self, repull=False, tag=None, show_print=True):
        base_image = f'{DOCKERHUB_URL}axonius/axonius-base-image'
        if tag:
            base_image = f'{base_image}:{tag}'
        return self._pull_image(base_image, repull, show_print)

    def build_libs(self, rebuild=False, base_image_tag=None, show_print=True):
        image_name = 'axonius/axonius-libs'
        output = subprocess.check_output(['docker', 'images', image_name]).decode('utf-8')
        image_exists = image_name in output
        if image_exists and not rebuild:
            if show_print:
                print('Image axonius-libs already built - skipping build step')
            return image_name
        runner = ParallelRunner()
        args = ['docker', 'build', '.', '-t', image_name]
        if base_image_tag:
            args.extend(['--build-arg', f'BASE_IMAGE_TAG={base_image_tag}'])
        runner.append_single('axonius-libs', args,
                             cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'axonius-libs')))
        assert runner.wait_for_all() == 0
        return image_name

    def build(self, system, adapter_names, plugin_names, standalone_services_names,
              mode='', rebuild=False, hard=False, async=True):
        to_build = [self.get_adapter(name) for name in adapter_names] + \
                   [self.get_plugin(name) for name in plugin_names] + \
                   [self.get_standalone_service(name) for name in standalone_services_names]
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
        settings.update_one(filter={'config_name': 'GuiService'},
                            update={'$set': {f'config.{SYSTEM_SETTINGS}': settings_dict}})

    def add_view(self, view_params):
        views = self.db.get_collection(self.gui.unique_name, 'device_views')
        views.insert_one(view_params)

    def set_research_rate(self, rate):
        settings = self.db.get_collection(self.scheduler.unique_name, CONFIGURABLE_CONFIGS_COLLECTION)
        settings.update_one(filter={'config_name': 'SystemSchedulerService'},
                            update={'$set': {'config.system_research_rate': rate}})

    def set_system_server_name(self, server_name):
        system_settings = self.db.get_collection(self.gui.unique_name, GUI_SYSTEM_CONFIG_COLLECTION)
        system_settings.replace_one({'type': 'server'}, {'type': 'server', 'server_name': server_name}, upsert=True)
