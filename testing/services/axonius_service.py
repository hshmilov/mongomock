import glob
import importlib
import inspect
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timedelta
from multiprocessing.pool import ThreadPool

import docker
import pytest

from axonius.consts.gui_consts import GUI_CONFIG_NAME, DEVICES_DIRECT_REFERENCES_COLLECTION, \
    DEVICES_INDIRECT_REFERENCES_COLLECTION, USERS_DIRECT_REFERENCES_COLLECTION, USERS_INDIRECT_REFERENCES_COLLECTION
from axonius.utils.debug import redprint
from axonius.utils.json import from_json
from conf_tools import TUNNELED_ADAPTERS
from install_utils import get_weave_subnet_ip_range
from scripts.instances.instances_modes import get_instance_mode, InstancesModes
from scripts.instances.network_utils import (get_encryption_key,
                                             restore_master_connection,
                                             get_docker_subnet_ip_range, DOCKER_BRIDGE_INTERFACE_NAME)
from axonius.consts.plugin_consts import (PLUGIN_UNIQUE_NAME, SYSTEM_SETTINGS, GUI_SYSTEM_CONFIG_COLLECTION,
                                          USER_VIEWS, DEVICE_VIEWS)
from axonius.consts.scheduler_consts import SCHEDULER_CONFIG_NAME
from axonius.consts.system_consts import (AXONIUS_DNS_SUFFIX, AXONIUS_NETWORK,
                                          NODE_MARKER_PATH,
                                          WEAVE_PATH, WEAVE_VERSION, DOCKERHUB_URL, USING_WEAVE_PATH,
                                          CUSTOMER_CONF_PATH)
from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD
from axonius.plugin_base import EntityType
from axonius.consts.plugin_consts import INSTANCE_CONTROL_PLUGIN_NAME
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
from services.plugins.openvpn_service import OpenvpnService
from services.plugins.static_correlator_service import StaticCorrelatorService
from services.plugins.static_users_correlator_service import StaticUsersCorrelatorService
from services.plugins.system_scheduler_service import SystemSchedulerService
from services.plugins.master_proxy_service import MasterProxyService
from services.standalone_services.remote_mongo_proxy_service import RemoteMongoProxyService
from services.standalone_services.tunneler_service import TunnelerService
from services.weave_service import is_weave_up, is_using_weave
from test_helpers.parallel_runner import ParallelRunner
from test_helpers.utils import try_until_not_thrown

DNS_REGISTER_POOL_SIZE = 5
CORE_ADDRESS = 'https://core.axonius.local'
REMOTE_CORE_WAIT_TIMEOUT = 20 * 60


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
        self.openvpn = OpenvpnService()
        self.instance_mode = get_instance_mode()
        self.remote_mongo = RemoteMongoProxyService() if \
            self.instance_mode == InstancesModes.remote_mongo.value else None

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
                                 self.master_proxy]

        # No instance control and OpenVPN on windows
        # Docker 'OperatingSystem' value is 'Docker Desktop' for OSX and Windows docker daemons and the linux version
        # for docker-ce./
        if 'linux' in sys.platform.lower() and docker.from_env().info()['OperatingSystem'] != 'Docker Desktop':
            self.axonius_services.append(self.instance_control)
            self.axonius_services.append(self.openvpn)

        self.entity_views = {
            EntityType.Devices: self.db.get_collection(self.gui.plugin_name, DEVICE_VIEWS),
            EntityType.Users: self.db.get_collection(self.gui.plugin_name, USER_VIEWS)
        }

        self.entity_views_direct_references = {
            EntityType.Devices: self.db.get_collection(self.gui.plugin_name, DEVICES_DIRECT_REFERENCES_COLLECTION),
            EntityType.Users: self.db.get_collection(self.gui.plugin_name, USERS_DIRECT_REFERENCES_COLLECTION)
        }

        self.entity_views_indirect_references = {
            EntityType.Devices: self.db.get_collection(self.gui.plugin_name, DEVICES_INDIRECT_REFERENCES_COLLECTION),
            EntityType.Users: self.db.get_collection(self.gui.plugin_name, USERS_INDIRECT_REFERENCES_COLLECTION)
        }

    @classmethod
    def get_is_docker_network_exists(cls):
        return cls._DOCKER_NETWORK_NAME in subprocess.check_output(['docker', 'network', 'ls', '--filter',
                                                                    f'name={cls._DOCKER_NETWORK_NAME}']).decode('utf-8')

    @classmethod
    def create_network(cls):
        if not is_weave_up() and 'linux' in sys.platform.lower() and \
                docker.from_env().info()['OperatingSystem'] != 'Docker Desktop':
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
        if not cls.get_is_docker_network_exists():
            print(f'Creating regular axonius network')
            docker_subnet_ip_range = get_docker_subnet_ip_range()
            subprocess.check_call(
                ['docker', 'network', 'create', f'--subnet={docker_subnet_ip_range}',
                 '--opt', f'com.docker.network.bridge.name={DOCKER_BRIDGE_INTERFACE_NAME}',
                 cls._DOCKER_NETWORK_NAME],
                stdout=subprocess.PIPE)

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
        weave_launch_command = [WEAVE_PATH, 'launch',
                                f'--dns-domain="{AXONIUS_DNS_SUFFIX}"', '--ipalloc-range', subnet_ip_range,
                                '--password',
                                encryption_key.strip()]
        subprocess.check_call(weave_launch_command)

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
            if expose_db and service_to_start in (self.db, self.remote_mongo):
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
        if self.instance_mode == InstancesModes.mongo_only.value:
            # we need to raise only mongo service
            services_to_start = [self.db, self.instance_control]
        else:
            services_to_start = self._process_internal_service_white_list(internal_service_white_list)

        if self.remote_mongo is not None:
            services_to_start = [self.remote_mongo if x.container_name == 'mongo' else x
                                 for x in services_to_start]
        mongo_service = next((x for x in services_to_start if x.container_name == 'mongo'), None)

        if mongo_service:
            # if mongo is also restarted, we can't restart anything else before it finishes
            mongo_service.take_process_ownership()
            _start_service(mongo_service)
            mongo_service.wait_for_service()
            services_to_start.remove(mongo_service)

        core_service = next((x for x in services_to_start if x.container_name == 'core'), None)
        if core_service:
            # if core is also restarted, we can't restart anything else before it finishes
            _start_service(core_service)
            core_service.wait_for_service()
            services_to_start.remove(core_service)

        gui_service = next((x for x in services_to_start if x.container_name == 'gui'), None)

        if gui_service:
            # if core is also restarted, we can't restart anything else before it finishes
            _start_service(gui_service)
            gui_service.wait_for_service()
            services_to_start.remove(gui_service)

        if self.instance_mode == InstancesModes.mongo_only.value and NODE_MARKER_PATH.is_file():
            # when running a mongo only instance, we want to wait for the master instance to be up
            # and then start up the rest of the services (for now, instance control)
            print(f'Waiting for {INSTANCE_CONTROL_PLUGIN_NAME} to be registered on core')
            self.wait_for_master_instance_control()

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

    def get_system_config_db(self):
        return self.db.get_collection(self.gui.unique_name, 'system_config')

    def get_aws_rules_db(self):
        return self.db.get_collection('compliance', 'aws_rules')

    def get_users_preferences_db(self):
        return self.db.gui_users_preferences_collection()

    def get_roles_db(self):
        return self.db.gui_roles_collection()

    def get_reports_config_db(self):
        return self.db.gui_reports_config_collection()

    def get_dashboard_spaces_db(self):
        return self.db.gui_dashboard_spaces_collection

    def get_dashboard_db(self):
        return self.db.gui_dashboard_collection

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

    @staticmethod
    def wait_for_master_instance_control(timeout=REMOTE_CORE_WAIT_TIMEOUT):
        tunnel = TunnelerService()
        tunnel.take_process_ownership()
        tunnel.start(mode='prod', allow_restart=True, show_print=False)
        start = time.time()
        while time.time() - start < timeout:
            try:
                output, err, _ = tunnel.run_command_in_container(
                    f'wget -O- --no-check-certificate {CORE_ADDRESS}/api/register',
                    shell='sh')
                if INSTANCE_CONTROL_PLUGIN_NAME in output.decode('ascii'):
                    break
            except Exception as e:
                print(f'{INSTANCE_CONTROL_PLUGIN_NAME} is not registered')
            time.sleep(5)
        return True

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
                if hasattr(service, 'plugin_name') and self._is_adapter_via_tunnel(service.plugin_name):
                    """
                    When adding --dns it means that if the dns request couldn't be resolved
                    from inside the docker network then the "docker dns server" will pass it to the entered dns servers
                    in the order of insert (in this instance it will first query 8.8.8.8 and only then if no
                    result it will query 192.167.255.2)

                    With that logic we make sure the order of resolving the DNS requests from inside
                    the tunneled adapters is as follows:
                    1) Inside the docker network (all the axonius.local suffixes"
                    2) The DNS server of the customer (192.167.255.2 is the IP of the customer's tunnel instance)
                    3) Global DNS server for general queries (Google Public DNS in this case)
                    """
                    service.start(mode, allow_restart=allow_restart, rebuild=rebuild,
                                  hard=hard, show_print=show_print, docker_internal_env_vars=env_vars,
                                  extra_flags=['--dns=192.167.255.2', '--dns=8.8.8.8'])
                else:
                    service.start(mode, allow_restart=allow_restart, rebuild=rebuild,
                                  hard=hard, show_print=show_print, docker_internal_env_vars=env_vars)

                service.wait_for_service(120)
                if service.should_register_unique_dns:
                    service.register_unique_dns()

                # Not all plugins have this function (such as mongo)
                if hasattr(service, 'handle_tunneled_container'):
                    service.handle_tunneled_container()
                return None
            except Exception as e:
                redprint(e)
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
        weave_images = [f'{DOCKERHUB_URL}weaveworks/weavedb', f'{DOCKERHUB_URL}weaveworks/weaveexec:{WEAVE_VERSION}',
                        f'{DOCKERHUB_URL}weaveworks/weave:{WEAVE_VERSION}']
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

    def pull_scalyr_image(self, repull=False, show_print=True):
        # scalyr agent image for further use
        scalyr_image = f'{DOCKERHUB_URL}scalyr/scalyr-agent-docker-json'
        return self._pull_image(scalyr_image, repull, show_print)

    def pull_container_alpine(self, repull=False, show_print=True):
        # Used for regular alpine containers (such as socat, openvpn, sshl)
        alpine_image = f'{DOCKERHUB_URL}alpine:3.11.6'
        return self._pull_image(alpine_image, repull, show_print)

    @staticmethod
    def _is_adapter_via_tunnel(adapter_name):
        if not CUSTOMER_CONF_PATH.is_file():
            return False
        data = from_json(CUSTOMER_CONF_PATH.read_bytes())
        if TUNNELED_ADAPTERS not in data:
            return False
        return adapter_name in data[TUNNELED_ADAPTERS]

    def pull_base_image(self, repull=False, tag=None, show_print=True):
        base_image = f'{DOCKERHUB_URL}axonius/axonius-base-image'
        if tag:
            base_image = f'{base_image}:{tag}'
        return self._pull_image(base_image, repull, show_print)

    @staticmethod
    def change_image_tag(image_name, new_tag='latest'):
        new_image_name = f'{image_name.split(":")[0]}:{new_tag}'
        if new_image_name == image_name:
            return image_name
        subprocess.check_call(shlex.split(f'docker tag {image_name} {new_image_name}'))
        return new_image_name

    def pull_manager_image(self, repull=False, tag=None, show_print=True):
        manager_image = f'{DOCKERHUB_URL}axonius/axonius-manager'
        if tag:
            manager_image = f'{manager_image}:{tag}'
        old_image_name = self._pull_image(manager_image, repull, show_print)
        return self.change_image_tag(old_image_name)

    def build_libs(self, rebuild=False, image_tag=None, show_print=True):
        image_name = 'axonius/axonius-libs'
        output = subprocess.check_output(['docker', 'images', image_name]).decode('utf-8')
        image_exists = image_name in output
        if image_exists and not rebuild:
            if show_print:
                print('Image axonius-libs already built - skipping build step')
            return image_name
        runner = ParallelRunner()
        args = ['docker', 'build', '.', '-t', image_name]
        if image_tag:
            args.extend(['--build-arg', f'BASE_IMAGE_TAG={image_tag}'])
        runner.append_single('axonius-libs', args,
                             cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'axonius-libs')))
        assert runner.wait_for_all() == 0
        return image_name

    def build(self, system, adapter_names, plugin_names, standalone_services_names,
              mode='', rebuild=False, hard=False, async=True, image_tag=None):
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
                service.build(mode, runner, image_tag=image_tag)
                time.sleep(1)  # We are getting resource busy. we suspect this is due parallel build storm
            assert runner.wait_for_all() == 0
        else:
            for service in to_build:
                images.append(service.image)
                if not rebuild and service.get_image_exists():
                    continue
                service.build(mode, image_tag=image_tag)
        return images

    @staticmethod
    def get_plugin_short_name(plugin_obj):
        short_name = os.path.basename(inspect.getfile(plugin_obj.__class__))
        assert short_name.endswith('_service.py')
        return short_name[:-len('_service.py')]

    def set_system_settings(self, settings_dict):
        self.db.plugins.gui.configurable_configs.update_config(
            GUI_CONFIG_NAME,
            {
                SYSTEM_SETTINGS: settings_dict
            }
        )

    def add_view(self, view_params):
        views = self.db.get_collection(self.gui.unique_name, 'device_views')
        views.insert_one(view_params)

    def set_research_rate(self, rate):
        self.db.plugins.system_scheduler.configurable_configs.update_config(
            SCHEDULER_CONFIG_NAME,
            {
                'system_research_rate': rate
            }
        )

    def set_system_server_name(self, server_name):
        system_settings = self.db.get_collection(self.gui.plugin_name, GUI_SYSTEM_CONFIG_COLLECTION)
        system_settings.replace_one({'type': 'server'}, {'type': 'server', 'server_name': server_name}, upsert=True)

    def clear_direct_references_collection(self, entity: EntityType):
        if entity == EntityType.Devices:
            return self.db.get_collection(self.gui.plugin_name, DEVICES_DIRECT_REFERENCES_COLLECTION).delete_many({})
        if entity == EntityType.Users:
            return self.db.get_collection(self.gui.plugin_name, USERS_DIRECT_REFERENCES_COLLECTION).delete_many({})
        return None
