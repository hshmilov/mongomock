import datetime
import logging
import os
import shlex
import socket
import struct
import time
from pathlib import Path
from typing import Dict, Iterable
import json

import requests
import paramiko
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from retrying import retry
from flask import jsonify

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts import instance_control_consts
from axonius.consts.gui_consts import Signup, LAST_UPDATED_FIELD
from axonius.consts.instance_control_consts import (InstanceControlConsts,
                                                    UPLOAD_FILE_SCRIPTS_PATH, UPLOAD_FILE_SCRIPT_NAME,
                                                    METRICS_INTERVAL_MINUTES,
                                                    MetricsFields, BOOT_CONFIG_FILE_PATH,
                                                    METRICS_CONTAINER_PATH, HOST_UPGRADE_MAGIC_FILEPATH)
from axonius.consts.plugin_consts import (PLUGIN_UNIQUE_NAME,
                                          PLUGIN_NAME,
                                          NODE_ID, GUI_PLUGIN_NAME, CORE_UNIQUE_NAME,
                                          BOOT_CONFIGURATION_SCRIPT_FILENAME, AXONIUS_MANAGER_PLUGIN_NAME,
                                          NODE_HOSTNAME)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.consts.scheduler_consts import SCHEDULER_CONFIG_NAME
from axonius.mixins.triggerable import RunIdentifier, Triggerable
from axonius.plugin_base import PluginBase, add_rule, return_error, is_db_restore_on_new_node
from axonius.utils.files import get_local_config_file
from axonius.utils.threading import LazyMultiLocker
from instance_control.snapshots_stats import calculate_snapshot

logger = logging.getLogger(f'axonius.{__name__}')


def get_default_gateway_linux() -> str:
    """
    Read the default gateway directly from /proc.
    """
    with open('/proc/net/route') as fh:
        for line in fh:
            fields = line.strip().split()
            if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                continue

            return socket.inet_ntoa(struct.pack('<L', int(fields[2], 16)))


def get_ssh_connection() -> paramiko.SSHClient:
    """
    Gets an SSHClient for the host machine
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    key = paramiko.RSAKey.from_private_key_file('/home/axonius/app/rsa_keys/id_rsa')   # directly parse as rsa
    client.connect(AXONIUS_MANAGER_PLUGIN_NAME, username='root', pkey=key)
    transport = client.get_transport()
    transport.set_keepalive(60)
    return client


def retry_if_parallelism_maxed(exception: paramiko.ChannelException):
    """
    If the exception is 'Administratively prohibited' it means we reachde the #MaxSessions config in the ssh
    In this case, let's retry soon
    """
    return isinstance(exception, paramiko.ChannelException) and exception.args == (1, 'Administratively prohibited')


def get_adapter_names_mappings(lines: Iterable[str]) -> Dict[str, str]:
    """
    Returns a mapping between plugin_name and the axonius_sh name from
    the output of `python devops/axonius_system.py ls`
    """
    linesiter = iter(lines)
    for x in linesiter:
        if 'Adapters:' in x:
            break
    res = {}
    for x in linesiter:
        if 'Standalone services:' in x:
            break
        sh_name, plugin_name = x.strip().split(', ')
        plugin_name = plugin_name.replace('-', '_')
        res[plugin_name] = sh_name
    return res


def log_file_and_return(file: paramiko.ChannelFile) -> str:
    """
    Logs to debug log and returns the result from the file
    :param file: to log and return
    :return: the data in the file
    """
    res = ''
    for x in file:
        logger.debug(x)
        res += x + '\n'
    return res


class InstanceControlService(Triggerable, PluginBase):
    """
    Has direct SSH communication with the host.
    Responsible on Adapter on Demand - starting and stopping adapters.
    """

    # List of service plugins supported by instance control
    SUPPORTED_SERVICE_PLUGINS = ['heavy_lifting', 'bandicoot', 'postgres', 'imagemagick']

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)
        # pylint: disable=W0511
        # TODO: Figure out if this connection has be refreshed from time to time
        self.__host_ssh = get_ssh_connection()
        self.__cortex_path = os.environ['CORTEX_PATH']
        self.__adapters = get_adapter_names_mappings(self.__exec_system_command('ls'))
        self.upgrade_started = False
        assert len(self.__adapters) > 100, f'Can not get all adapters mappings, got just {self.__adapters}'

        logger.info('Got SSH and adapter names mapping')
        logger.debug(self.__adapters)

        self.__lazy_locker = LazyMultiLocker()

        # RESTORE ON NEW NODE
        self.update_hostname_after_restore_on_new_node()

        # Create plugin cleaner thread
        executors = {'default': ThreadPoolExecutor(1)}
        self.send_instance_data_thread = LoggedBackgroundScheduler(executors=executors)
        self.send_instance_data_thread.add_job(func=self.__get_node_metadata,
                                               trigger=IntervalTrigger(minutes=METRICS_INTERVAL_MINUTES),
                                               next_run_time=datetime.datetime.now(),
                                               name='send_instance_data',
                                               id='send_instance_data',
                                               max_instances=1,
                                               coalesce=True)
        self.send_instance_data_thread.start()

    def _delayed_initialization(self):
        self.run_boot_config_file()

    def run_boot_config_file(self):
        try:
            if BOOT_CONFIG_FILE_PATH.exists():
                if BOOT_CONFIG_FILE_PATH.stat().st_size > 0:
                    self.execute_configuration_script_on_host(BOOT_CONFIGURATION_SCRIPT_FILENAME)
                else:
                    logger.debug('deleting empty boot configuration file')
                    BOOT_CONFIG_FILE_PATH.unlink()
        except Exception:
            logger.exception('Error running boot config file')

    def trigger_execute_shell(self, post_json: dict):
        logger.info(f'Got execute shell triggerable with post_json: {str(post_json)}')
        if 'cmd' not in post_json:
            raise RuntimeError(f'Malformed post_json dict')
        return self.__exec_command_verbose(post_json['cmd'], environment=post_json.get('environment'))

    # pylint: disable=too-many-return-statements
    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        """
        start:<plugin_name> or stop:<plugin_name>
        post_json is ignored
        Starts or stops the given plugin. Only works on adapters.
        """
        if self.upgrading_cluster_in_prog:
            raise RuntimeError('Upgrade in progress')

        if job_name == 'execute_shell':
            return self.trigger_execute_shell(post_json)

        parsed_path = job_name.split(':')
        if len(parsed_path) != 2:
            raise RuntimeError('Wrong job_name')
        operation_type, plugin_name = parsed_path
        if operation_type not in ['start', 'stop', 'run']:
            raise RuntimeError('Wrong job_name')
        del parsed_path

        with self.__lazy_locker.get_lock([plugin_name]):

            if plugin_name in self.SUPPORTED_SERVICE_PLUGINS:
                # quick hack
                if operation_type == 'start':
                    return self.start_service(plugin_name)
                if operation_type == 'run':
                    return self.run_service(plugin_name, post_json)
                # else - stop
                return self.stop_service(plugin_name)
            sh_plugin_name = self.__adapters.get(plugin_name)
            if sh_plugin_name:
                if operation_type == 'start':
                    return self.start_adapter(sh_plugin_name)
                # else - stop
                return self.stop_adapter(sh_plugin_name)
            return ''

    @add_rule(InstanceControlConsts.EnterUpgradeModeEndpoint, methods=['GET'], should_authenticate=False)
    def enter_upgrade_mode(self):
        logger.info(f'Entering pre-upgrade mode ...')
        self.upgrading_cluster_in_prog = True
        return log_file_and_return(self.__exec_system_command(f'adapter all down'))

    @add_rule(InstanceControlConsts.ReadProxySettings, methods=['GET'], should_authenticate=False)
    def read_proxy_settings(self):
        logging.info(f'Returning proxy settings')
        return jsonify(self._proxy_settings)

    # pylint: disable=no-self-use
    @add_rule(InstanceControlConsts.PullUpgrade, methods=['GET'], should_authenticate=False)
    def pull_upgrade(self):
        logger.info(f'Starting download')

        url = f'http://httpd-service.axonius.local/upgrade.py'
        r = requests.get(url)
        with open('/home/axonius/app/instance_control/upgrade.py', 'wb') as f:
            f.write(r.content)
        logger.info(f'Download completed')

        return 'Download completed'

    @add_rule(InstanceControlConsts.TriggerUpgrade, methods=['GET'], should_authenticate=False)
    def trigger_upgrade(self):
        if self.upgrade_started:
            logger.info(f'Upgrade already running')
            return 'Upgrade in progress'

        logger.info(f'Running the upgrade')
        self.upgrade_started = True
        return log_file_and_return(
            self.__upgrade_host()
        )

    @add_rule(InstanceControlConsts.DescribeClusterEndpoint, methods=['GET'], should_authenticate=False)
    def describe_cluster(self):
        instance_projection = {
            PLUGIN_UNIQUE_NAME: True,
            NODE_ID: True,
            'status': True,
            'last_seen': True,
            '_id': False
        }
        my_plugin_entity = self.core_configs_collection.find_one({
            PLUGIN_UNIQUE_NAME: self.plugin_unique_name
        }, projection=instance_projection)
        instances = self.core_configs_collection.find({PLUGIN_NAME: 'instance_control'}, projection=instance_projection)
        signup_collection = self._get_collection(Signup.SignupCollection, db_name=GUI_PLUGIN_NAME)
        signup = signup_collection.find_one({})
        if signup:
            signup.pop('_id', None)
            signup['newPassword'] = ''

        active_nodes = [x['node_id'] for x in self.nodes_metadata_collection.find({'status': {'$ne': 'Deactivated'}})]
        # filter out inactive instance-control's
        instances = [x for x in instances if x['node_id'] in active_nodes]

        result = {
            'my_entity': my_plugin_entity,
            'instances': instances,
            'signup': signup
        }
        return jsonify(result)

    def _update_hostname(self, hostname):
        hostname_change_file = '/home/ubuntu/cortex/uploaded_files/hostname_change'
        current_hostname = instance_control_consts.HOSTNAME_FILE_PATH.read_text().strip()
        logger.info(f'Start updating axonius node hostname, current:{current_hostname} new:{hostname} . . . ')
        cmd = f'/bin/sh -c "echo {hostname} > {hostname_change_file}"'
        self.__exec_command_verbose(cmd)
        # Theoretically that best way to do the validation is map the /etc/hostname file from
        # the host to the container, but because every change in hostname causing the file to re-create
        # and therefore change the inode originally mapped to the docker container, so we just check that
        # the task deleted the original hostname_change file in order to make sure it worked
        # We decided that mapping the whole /etc folder in order to solve this it too dangerous
        if Path(hostname_change_file).exists():
            time.sleep(3)
        instance_control_consts.HOSTNAME_FILE_PATH.write_text(f'{hostname}\n')
        logger.debug(f'Hostname {hostname} updated successfully')

    @add_rule('instances/host/<hostname>', methods=['PUT'], should_authenticate=False)
    def update_hostname(self, hostname):
        """
        update instance hostname by calling hostnamectl set-hostname.
        """
        try:
            self._update_hostname(hostname)
            return 'Success'
        except Exception:
            logger.exception('fatal error during hostname update ')
            return return_error(f'fatal error during hostname update   ', 500)

    @add_rule(InstanceControlConsts.FileExecute, methods=['POST'], should_authenticate=False)
    def file_execute(self):
        data = self.get_request_data_as_object()
        file_docker_path = data.get('path', None)

        if not Path(file_docker_path).exists():
            logger.error(f'execute_file: file not exist at:{file_docker_path}')
            return return_error('file not exist', 404)
        self.execute_configuration_script_on_host()
        return 'file executed successfully'

    def execute_configuration_script_on_host(self, config_script_path=''):
        execution_script_path = Path(UPLOAD_FILE_SCRIPTS_PATH, UPLOAD_FILE_SCRIPT_NAME)
        # copy execution python script aka axcs
        local_file_name = '/home/ubuntu/axcs.py'
        copy_cmd = f'cp {execution_script_path} {local_file_name}'
        self.__exec_command_verbose(copy_cmd)
        # chmod the axcs
        chmod_cmd = f'chmod +x {local_file_name}'
        self.__exec_command_verbose(chmod_cmd)
        # run the axcs
        timestamp = datetime.datetime.utcnow().strftime('%Y_%m_%d_%H_%M_%S')
        nohup_logs_directory = Path('/home/ubuntu/logs/axonius/offline')
        # create directory for logging the nohup action
        mkdir_cmd = 'mkdir -p /home/ubuntu/logs/axonius/offline'
        self.__exec_command_verbose(mkdir_cmd)
        nohup_log_file_name = f'{nohup_logs_directory}/axonius_axcs.{timestamp}.log'
        logger.info(f'execute_file: got file to execute, follow up in host at '
                    f'{nohup_log_file_name}')

        cmd = f'nohup {local_file_name} {config_script_path} > {nohup_log_file_name} 2>&1 &'
        self.__exec_command_verbose(cmd)
        return True

    def __get_node_metadata(self):
        logger.info('Starting Thread: Sending instance data to core.')
        return_val = 'Success'

        try:
            hostname = instance_control_consts.HOSTNAME_FILE_PATH.read_text().strip()

            result = self.request_remote_plugin(f'node/{self.node_id}', method='post', json={'key': 'hostname',
                                                                                             'value': hostname})
            if result.status_code != 200:
                return_val = 'Failure'
                logger.error(
                    f'Something went wrong while updating the node\'s hostname: {result.status_code}, {result.content}')
        except Exception as e:
            logger.exception(f'Something went wrong while updating the node\'s hostname: {e}')

        node_metrics = self._get_node_metrics()

        result = self.request_remote_plugin(f'node/{self.node_id}', method='post', json={'key': 'metrics',
                                                                                         'value': node_metrics})
        if result.status_code != 200:
            logger.error(
                f'Something went wrong while updating the node\'s metrics: {result.status_code}, {result.content}')
            return_val = 'Failure'
        return return_val

    def _get_node_metrics(self):
        try:
            logger.info('Getting node metrics')

            res = METRICS_CONTAINER_PATH.read_text()

            if res:
                metrics_result = json.loads(res)
            else:
                logger.error('Unable to get node metrics data')
                return {}

            if self._is_running_on_master():
                logger.info('Getting master snapshots stats')
                retention_days = None
                config = self.plugins.system_scheduler.configurable_configs[SCHEDULER_CONFIG_NAME]
                history_settings = config['history_retention_settings']
                if history_settings.get('enabled') and history_settings.get('max_days_to_save') > 0:
                    retention_days = history_settings.get('max_days_to_save')

                max_snapshot_days, snapshot_days_left, last_snapshot_size = \
                    calculate_snapshot(metrics_result['metrics'].get(MetricsFields.DataDiskSize, 0),
                                       metrics_result['metrics'].get(MetricsFields.DataDiskFreeSpace, 0),
                                       retention_days)
                metrics_result['metrics'][MetricsFields.LastSnapshotSize] = last_snapshot_size
                metrics_result['metrics'][MetricsFields.RemainingSnapshotDays] = snapshot_days_left
                metrics_result['metrics'][MetricsFields.MaxSnapshots] = max_snapshot_days

            logger.debug(f'metrics result: {metrics_result}')

            errors = metrics_result.get('errors')
            if errors and len(errors) > 0:
                logger.error(f'Metrics errors: {errors}')

            metrics_result['metrics'][LAST_UPDATED_FIELD] = datetime.datetime.now()
            return metrics_result['metrics']
        except Exception:
            logger.exception('fatal error during node metrics calculation')
            return {LAST_UPDATED_FIELD: datetime.datetime.now()}

    def __exec_system_command(self, cmd: str, environment: dict = None) -> paramiko.ChannelFile:
        """
        Executes an axonius_system.py command
        PWD is the cortex directory
        :param cmd: command to execute
        :param environment: the environment variables
        :return: stdout
        """
        return self.__exec_command(f'cd {self.__cortex_path}; ./pyrun.sh devops/axonius_system.py {cmd}', environment)

    @retry(wait_fixed=10000,
           stop_max_delay=120000,
           retry_on_exception=retry_if_parallelism_maxed)
    def __exec_command(self, cmd: str, environment: dict = None) -> paramiko.ChannelFile:
        """
        Executes a command on the host using ssh
        :param cmd: command to execute
        :return: stdout
        """
        transport = self.__host_ssh.get_transport()
        if not transport.is_active():
            self.__host_ssh = get_ssh_connection()
        _, stdout, _ = self.__host_ssh.exec_command(cmd, environment=environment)
        return stdout

    def __upgrade_host(self, environment: dict = None) -> paramiko.ChannelFile:
        """
        Puts a file on specific directory that causes the axonius system to upgrade
        :param cmd: command to execute
        :return: stdout
        """
        return self.__exec_command(cmd=f'touch {HOST_UPGRADE_MAGIC_FILEPATH}', environment=environment)

    @retry(wait_fixed=10000,
           stop_max_delay=120000,
           retry_on_exception=retry_if_parallelism_maxed)
    def __exec_command_verbose(self, cmd: str, environment: dict = None) -> paramiko.ChannelFile:
        """
        Executes a command on the host using ssh and log stdout and stderr streams .
        command doesn't return stdout .
        :param cmd: command to execute
        """
        transport = self.__host_ssh.get_transport()
        if not transport.is_active():
            self.__host_ssh = get_ssh_connection()
        _, stdout, stderr = self.__host_ssh.exec_command(cmd, environment=environment)
        err = stderr.read().decode('utf-8').strip()
        out = stdout.read().decode('utf-8').strip()
        logger.debug(f'[ExecCmd] {err} ; {out} ')

        return out

    def start_adapter(self, adapter_name: str):
        """
        (Re) Starts an adapter
        :param adapter_name: the adapter name to start, e.g. 'ad', 'aws' or 'qualys'
        :return: the output of the command
        """
        return log_file_and_return(self.__exec_system_command(f'adapter {adapter_name} up --restart --prod'))

    def stop_adapter(self, adapter_name: str):
        """
        Stops an adapter
        :param adapter_name: the adapter name to stop, e.g. 'ad', 'aws' or 'qualys'
        :return: the output of the command
        """
        return log_file_and_return(self.__exec_system_command(f'adapter {adapter_name} down'))

    def start_service(self, service_name: str):
        """
        (Re) Starts a service
        :param service_name: the service name to start
        :return: the output of the command
        """
        return log_file_and_return(self.__exec_system_command(f'service {service_name} up --restart --prod'))

    def run_service(self, service_name: str, parameters: dict = None):
        """
        Runs a service
        :param service_name: the service name to run
        :param parameters: the params for the run
        :return: the output of the command
        """
        parameters_string = ' '.join([f'{shlex.quote(key)}={shlex.quote(parameters[key])}'
                                      for key in parameters.keys()])
        command = f'service {service_name} run --env {parameters_string}'
        logger.info(f'Running {command}')
        return log_file_and_return(self.__exec_system_command(command))

    def stop_service(self, service_name: str):
        """
        Stops a service
        :param service_name: the adapter name to stop
        :return: the output of the command
        """
        return log_file_and_return(self.__exec_system_command(f'service {service_name} down'))

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.NotRunning

    def _is_running_on_master(self) -> bool:
        return self.node_id == self.core_configs_collection.find_one({'plugin_name': CORE_UNIQUE_NAME})['node_id']

    def update_hostname_after_restore_on_new_node(self):
        if is_db_restore_on_new_node() and self._is_running_on_master():
            # reloading after db restore on new node
            # update hostname with backup node hostname
            hostname_from_backup = self.nodes_metadata_collection.find_one(
                {NODE_ID: self.node_id}, {'_id': 0, NODE_HOSTNAME: 1})

            try:
                if hostname_from_backup:
                    self._update_hostname(hostname_from_backup.get(NODE_HOSTNAME))
                    logger.info(f'DB restored on new node hostname set to {hostname_from_backup.get(NODE_HOSTNAME)}')
                else:
                    logger.error(f'skipping hostname update after restore because missing hostname missing on metadata')

            except Exception:
                logger.error(f'Failure updating hostname {hostname_from_backup} '
                             f'after DB restore with node id {self.node_id}')
