import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import docker
import paramiko
import pytest
from retrying import retry

from axonius.consts.system_consts import CUSTOMER_CONF_PATH
from axonius.utils.wait import wait_until
from builds import Builds
from builds.builds_factory import BuildsInstance
from deployment.install import SYSTEM_BOOT_CRON_SCRIPT_PATH
from devops.scripts.instances.system_boot import \
    BOOTED_FOR_PRODUCTION_MARKER_PATH
from scripts.instances.instances_consts import CORTEX_PATH
from test_credentials.test_nexpose_credentials import client_details
from ui_tests.tests.ui_test_base import TestBase

NODE_MAKER_USERNAME = 'node_maker'
NODE_MAKER_PASSWORD = 'M@ke1tRain'

DEFAULT_IMAGE_USERNAME = 'ubuntu'
DEFAULT_IMAGE_PASSWORD = 'bringorder'
AUTO_TEST_VM_KEY_PAIR = 'Auto-Test-VM-Key'

RESTART_LOG_PATH = Path(f'/var/log/{os.path.basename(SYSTEM_BOOT_CRON_SCRIPT_PATH).split(".")[0]}.log')

DEFAULT_LIMIT = 10
MAX_CHARS = 10 ** 9
SSH_CHANNEL_TIMEOUT = 60 * 35
NODE_NAME = 'node_1'
NODE_HOSTNAME = 'node-test-hostname'
NEXPOSE_ADAPTER_NAME = 'Rapid7 Nexpose'
NEXPOSE_ADAPTER_FILTER = 'adapters == "nexpose_adapter"'
PRIVATE_IP_ADDRESS_REGEX = r'inet (10\..*|192\.168.*|172\..*)\/'

# Don't add Nexpose, AD
CUSTOMER_CONF = json.dumps({
    'exclude-list': {
        'add-to-exclude': [
            'nessus',
            'carbonblack_defense',
            'minerva',
            'desktop_central',
            'tenable_io',
            'clearpass',
            'device42',
            'symantec_cloud_workload',
            'cisco_meraki',
            'paloalto_panorama',
            'infinite_sleep',
            'openstack',
            'quest_kace',
            'alibaba',
            'tripwire_enterprise',
            'jamf',
            'azure',
            'cisco_prime',
            'observeit',
            'alertlogic',
            'lansweeper',
            'nmap',
            'duo',
            'unifi',
            'promisec',
            'symantec_ee',
            'proxmox',
            'kaseya',
            'aws',
            'mssql',
            'blackberry_uem',
            'azure_ad',
            'aruba',
            'gotoassist',
            'cynet',
            'riverbed',
            'sentinelone',
            'ibm_tivoli_taddm',
            'okta',
            'chef',
            'redseal',
            'armis',
            'qualys_scans',
            'truefort',
            'illusive',
            'fireeye_hx',
            'traiana_lab_machines',
            'malwarebytes',
            'sccm',
            'twistlock',
            'linux_ssh',
            'cybereason',
            'foreman',
            'esx',
            'bluecat',
            'bomgar',
            'checkpoint_r80',
            'junos',
            'fortigate',
            'juniper',
            'nimbul',
            'infoblox',
            'epo',
            'google_mdm',
            'mobi_control',
            'cisco_amp',
            'dynatrace',
            'logrhythm',
            'deep_security',
            'absolute',
            'carbonblack_response',
            'forcepoint_csv',
            'sophos',
            'zabbix',
            'mobileiron',
            'cisco_umbrella',
            'tenable_security_center',
            'saltstack_enterprise',
            'cloudflare',
            'json_file',
            'stresstest',
            'softlayer',
            'opswat',
            'saltstack',
            'counter_act',
            'qcore',
            'splunk',
            'divvycloud',
            'airwatch',
            'cylance',
            'redcloack',
            'cisco_ise',
            'dropbox',
            'spacewalk',
            'carbonblack_protection',
            'oracle_vm',
            'redcanary',
            'stresstest_scanner',
            'eset',
            'ensilo',
            'service_now',
            'puppet',
            'code42',
            'hyper_v',
            'gce',
            'csv',
            'snipeit',
            'sysaid',
            'oracle_cloud',
            'nessus_csv',
            'claroty',
            'symantec',
            'stresstest_users',
            'datadog',
            'symantec_altiris',
            'tanium',
            'crowd_strike',
            'bigfix',
            'shodan',
            'cisco',
            'cloudpassage',
            'webroot',
            'samange',
            'bitdefender',
            'secdo',
            'bitsight',
            'ca_cmdb',
            'cisco_firepower_management_center',
            'datto_rmm',
            'endgame',
            'censys',
            'druva',
            'f5_icontrol',
            'cycognito',
            'automox',
            'haveibeenpwned',
            'indegy',
            'kaspersky_sc',
            'maas360',
            'imperva_dam',
            'jumpcloud',
            'librenms',
            'netbox',
            'office_scan',
            'paloalto_cortex',
            'signalsciences',
            'symantec_12',
            'rumble',
            'solarwinds_orion',
            'symantec_sep_cloud',
            'zscaler'
        ],
        'remove-from-exclude': []
    }
})


@retry(stop_max_attempt_number=180, wait_fixed=1000 * 20)
def wait_for_booted_for_production(instance: BuildsInstance):
    print('Waiting for server to be booted for production...')
    test_ready_command = f'ls -al {BOOTED_FOR_PRODUCTION_MARKER_PATH.absolute().as_posix()}'
    state = instance.ssh(test_ready_command)
    assert 'root root' in state[1]


def bring_restart_on_reboot_node_log(instance: BuildsInstance, logger):
    get_log_command = f'tail {RESTART_LOG_PATH.as_posix()} -n 50'
    restart_log_tail = instance.ssh(get_log_command)
    logger.info(f'{RESTART_LOG_PATH} : {restart_log_tail[1]}')
    try:
        get_log_command = f'cat {RESTART_LOG_PATH.as_posix()}'
        restart_log_tail = instance.ssh(get_log_command)
        logger.info(f'{RESTART_LOG_PATH} : {restart_log_tail[1]}')

        logs_path = Path(CORTEX_PATH) / 'logs'
        logs_dir = instance.ssh(f'ls -la {logs_path}')
        logger.info(f'\n\nLogs dir:\n {logs_dir}')
        folder_as_tar = instance.get_folder_as_tar(logs_path)
        logger.info(f'Got {len(folder_as_tar)} bytes from instance')
        (logs_path / 'ui_logger' / 'instance_logs_tar.tar').write_bytes(folder_as_tar)
    except Exception:
        logger.info(f'Failed bringing full log', exc_info=True)


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
            now = datetime.now()
            logger.info('Waiting for server to boot to production')
            try:
                wait_for_booted_for_production(current_instance)
            except Exception:
                bring_restart_on_reboot_node_log(current_instance, logger)
                logger.info(f'Failed once, trying again, failed after {(datetime.now() - now).total_seconds()}')
                wait_for_booted_for_production(current_instance)

            logger.info(f'Server is booted for production, took {(datetime.now() - now).total_seconds()}')
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
        def read_until(ssh_chan: paramiko.Channel, what):
            data = b''
            try:
                for _ in range(MAX_CHARS):
                    received = ssh_chan.recv(30)
                    self.logger.info(f'Data read is: {received.decode("utf-8")}')
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
        chan: paramiko.Channel = ssh_client.get_transport().open_session()
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

    def put_customer_conf_file(self):
        instance = self._instances[0]
        instance.put_file(file_object=io.StringIO(CUSTOMER_CONF),
                          remote_file_path=str(CUSTOMER_CONF_PATH))

    def _add_nexpose_adadpter_and_discover_devices(self):
        # Using nexpose on all these test since i do not raise
        # nexpose as part of the tests so the only nexpose adapter present
        # should be from the node (and the client add should only have that option)
        # and for any reason it is not present than we have an instances bug.
        self.adapters_page.add_server(client_details, adapter_name=NEXPOSE_ADAPTER_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.base_page.run_discovery()
        wait_until(lambda: self._check_device_count() > 1, total_timeout=200, interval=20)

    def _check_device_count(self):
        self.devices_page.switch_to_page()
        self.devices_page.refresh()
        self.devices_page.run_filter_query(NEXPOSE_ADAPTER_FILTER)
        return self.devices_page.count_entities()

    def _delete_nexpose_adapter_and_data(self):
        self.adapters_page.remove_server(adapter_name=NEXPOSE_ADAPTER_NAME, delete_associated_entities=True)
        @retry(stop_max_attempt_number=100, wait_fixed=2000)
        def to_check():
            assert self._check_device_count() == 0
        to_check()

    def check_ssh_tunnel(self):
        test_string = 'I Am Here'
        test_filename = 'successful_ssh.txt'

        # Writing file to test ssh using the tunnel.
        for instance in self._instances:
            rc, out = instance.ssh(f'echo "{test_string}" > {test_filename}')
            if rc != 0:
                self.logger.info(f'Writing test ssh tunnel file failed.')

        # Commands to execute from a container (in-order to make use of our weave net vx-lan).
        commands = ['apt update', 'apt install sshpass',
                    f'sshpass -p{DEFAULT_IMAGE_PASSWORD} ssh -o StrictHostKeyChecking=no -p 9958 '
                    f'{DEFAULT_IMAGE_USERNAME}@tunnler.axonius.local "cat {test_filename}"']
        client = docker.from_env()
        core = client.containers.list(filters={'name': 'core'})[0]

        res = None
        for current_command in commands:
            res = core.exec_run(current_command)

            if res.exit_code != 0:
                self.logger.error(f'Failed to run command on core container: {current_command}')
                raise Exception(f'Failed to run command on core container: {current_command}')

        assert test_string in res.output.decode('utf-8'), 'Failed to use ssh tunnel to ssh to instance.'
