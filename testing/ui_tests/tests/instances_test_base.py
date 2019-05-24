import os
import re
import subprocess
import sys
from pathlib import Path

import paramiko
import pytest
from retrying import retry

from builds import Builds
from builds.builds_factory import BuildsInstance
from devops.scripts.instances.start_system_on_first_boot import BOOTED_FOR_PRODUCTION_MARKER_PATH
from test_credentials.test_nexpose_credentials import client_details

from ui_tests.tests.ui_test_base import TestBase
from axonius.utils.wait import wait_until

NODE_MAKER_USERNAME = 'node_maker'
NODE_MAKER_PASSWORD = 'M@ke1tRain'

DEFAULT_IMAGE_USERNAME = 'ubuntu'
DEFAULT_IMAGE_PASSWORD = 'bringorder'
AUTO_TEST_VM_KEY_PAIR = 'Auto-Test-VM-Key'

RESTART_LOG_PATH = Path('/var/log/start_system_on_reboot.log')

DEFAULT_LIMIT = 10

MAX_CHARS = 10 ** 9
SSH_CHANNEL_TIMEOUT = 60 * 35
NODE_NAME = 'node_1'
NEXPOSE_ADAPTER_NAME = 'Rapid7 Nexpose'
NEXPOSE_ADAPTER_FILTER = 'adapters == "nexpose_adapter"'
PRIVATE_IP_ADDRESS_REGEX = r'inet (10\..*|192\.168.*|172\..*)\/'


@retry(stop_max_attempt_number=90, wait_fixed=1000 * 20)
def wait_for_booted_for_production(instance: BuildsInstance):
    print('Waiting for server to be booted for production...')
    test_ready_command = f'ls -al {BOOTED_FOR_PRODUCTION_MARKER_PATH.absolute().as_posix()}'
    state = instance.ssh(test_ready_command)
    assert 'root root' in state[1]


def bring_restart_on_reboot_node_log(instance: BuildsInstance, logger):
    get_log_command = f'tail {RESTART_LOG_PATH.absolute().as_posix()}'
    restart_log_tail = instance.ssh(get_log_command)
    logger.info(f'/var/log/start_system_on_reboot.log : {restart_log_tail[1]}')


def setup_instances(logger, instance_name, export_name=None):
    builds_instance = Builds()
    if export_name:
        latest_export = builds_instance.get_export_by_name(export_name)
    else:
        latest_export = builds_instance.get_latest_daily_export()
    logger.info(f'using {latest_export["version"]} for instances tests')

    def create_instances_helper():
        ret, _ = builds_instance.create_instances(
            f'test_latest_export_{instance_name} ' + (os.environ.get('TEST_GROUP_NAME') or ''),
            't2.2xlarge',
            1,
            instance_cloud=Builds.CloudType.AWS,
            instance_image=latest_export['ami_id'],
            predefined_ssh_username=DEFAULT_IMAGE_USERNAME,
            predefined_ssh_password=DEFAULT_IMAGE_PASSWORD,
            key_name=AUTO_TEST_VM_KEY_PAIR,
            network_security_options=Builds.NetworkSecurityOptions.NoInternet
        )
        return ret

    instances = wait_until(create_instances_helper, check_return_value=True,
                           tolerated_exceptions_list=[ValueError], interval=2)

    for current_instance in instances:
        current_instance.wait_for_ssh()
        try:
            wait_for_booted_for_production(current_instance)
            logger.info('Server is booted for production.')
        except Exception:
            bring_restart_on_reboot_node_log(current_instance, logger)
            # If we fail in setup_method, teardown will not be called. lets terminate the instance.
            current_instance.terminate()
            raise

    return instances


class TestInstancesBase(TestBase):
    def setup_method(self, method):
        super().setup_method(method)
        export_name = pytest.config.option.export_name
        self._instances = setup_instances(self.logger, self.__class__.__name__, export_name=export_name)

    def teardown_method(self, method):
        for current_instance in self._instances:
            try:
                current_instance.terminate()
            except Exception as e:
                print(f'Could not terminate {current_instance}: {e}, bypassing', file=sys.stderr, flush=True)

        super().teardown_method(method)

    @staticmethod
    def connect_node_maker(instance, password=NODE_MAKER_PASSWORD):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(instance.ip, username=NODE_MAKER_USERNAME, password=password, timeout=60,
                       auth_timeout=60, look_for_keys=False, allow_agent=False)
        return client

    def join_node(self):
        def read_until(ssh_chan, what):
            data = b''
            try:
                for _ in range(MAX_CHARS):
                    received = ssh_chan.recv(1024)
                    if not received:
                        raise RuntimeError('Connection Closed')
                    data += received
                    if data.endswith(what):
                        break
                return data
            except Exception:
                self.logger.exception(f'failed read_until: {what}')
                self.logger.error(f'data received until failure: {data}')
                raise

        ip_output = subprocess.check_output(['ip', 'a']).decode('utf-8')
        master_ip_address = re.search(PRIVATE_IP_ADDRESS_REGEX, ip_output).group(1)
        node_join_token = self.instances_page.get_node_join_token()
        ssh_client = self.connect_node_maker(self._instances[0])
        chan = ssh_client.get_transport().open_session()
        chan.settimeout(SSH_CHANNEL_TIMEOUT)
        chan.invoke_shell()
        node_join_message = read_until(chan, b'Please enter connection string:')
        self.logger.info(f'node_maker login message: {node_join_message.decode("utf-8")}')
        chan.sendall(f'{master_ip_address} {node_join_token} {NODE_NAME}\n')
        try:
            node_join_log = read_until(chan, b'Node successfully joined Axonius cluster.\n')
            self.logger.info(f'node join log: {node_join_log.decode("utf-8")}')
        except Exception:
            self.logger.exception('Failed to connect node.')
            raise

        self.instances_page.wait_until_node_appears_in_table(NODE_NAME)

    def _add_nexpose_adadpter_and_discover_devices(self):
        # Using nexpose on all these test since i do not raise
        # nexpose as part of the tests so the only nexpose adapter present
        # should be from the node (and the client add should only have that option)
        # and for any reason it is not present than we have an instances bug.
        self.adapters_page.add_server(client_details, adapter_name=NEXPOSE_ADAPTER_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.base_page.run_discovery()
        wait_until(lambda: self._check_device_count() > 1, total_timeout=90, interval=20)

    def _check_device_count(self):
        self.devices_page.switch_to_page()
        self.devices_page.refresh()
        self.devices_page.run_filter_query(NEXPOSE_ADAPTER_FILTER)
        return self.devices_page.count_entities()

    def _delete_nexpose_adapter_and_data(self):
        self.adapters_page.remove_server(adapter_name=NEXPOSE_ADAPTER_NAME, delete_associated_entities=True)
        wait_until(lambda: self._check_device_count() == 0, total_timeout=90, interval=20)
