import datetime
import logging
import socket
import struct
from typing import Dict, Iterable

import paramiko
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from retrying import retry

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts import instance_control_consts
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.mixins.triggerable import RunIdentifier, Triggerable
from axonius.plugin_base import PluginBase
from axonius.utils.files import get_local_config_file
from axonius.utils.threading import LazyMultiLocker

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
    client.connect(get_default_gateway_linux(), username='ubuntu', key_filename='/home/axonius/app/rsa_keys')
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

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)
        # pylint: disable=W0511
        # TODO: Figure out if this connection has be refreshed from time to time
        self.__host_ssh = get_ssh_connection()
        self.__adapters = get_adapter_names_mappings(self.__exec_system_command('ls'))
        assert len(self.__adapters) > 100, f'Can not get all adapters mappings, got just {self.__adapters}'

        logger.info('Got SSH and adapter names mapping')
        logger.debug(self.__adapters)

        self.__lazy_locker = LazyMultiLocker()

        # Create plugin cleaner thread
        executors = {'default': ThreadPoolExecutor(1)}
        self.send_instance_data_thread = LoggedBackgroundScheduler(executors=executors)
        self.send_instance_data_thread.add_job(func=self.__get_hostname_and_ips,
                                               trigger=IntervalTrigger(hours=1),
                                               next_run_time=datetime.datetime.now(),
                                               name='send_instance_data',
                                               id='send_instance_data',
                                               max_instances=1,
                                               coalesce=True)
        self.send_instance_data_thread.start()

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        """
        start:<plugin_name> or stop:<plugin_name>
        post_json is ignored
        Starts or stops the given plugin. Only works on adapters.
        """
        parsed_path = job_name.split(':')
        if len(parsed_path) != 2:
            raise RuntimeError('Wrong job_name')
        operation_type, plugin_name = parsed_path
        if operation_type not in ['start', 'stop']:
            raise RuntimeError('Wrong job_name')
        del parsed_path

        with self.__lazy_locker.get_lock([plugin_name]):
            sh_plugin_name = self.__adapters[plugin_name]
            if operation_type == 'start':
                return self.start_adapter(sh_plugin_name)
            # else - stop
            return self.stop_adapter(sh_plugin_name)

    def __get_hostname_and_ips(self):
        logger.info('Starting Thread: Sending instance data to core.')
        return_val = 'Success'
        hostname = instance_control_consts.HOSTNAME_FILE_PATH.read_text().strip()
        ips = []

        result = self.request_remote_plugin(f'node/{self.node_id}', method='post', json={'key': 'hostname',
                                                                                         'value': hostname})
        if result.status_code != 200:
            return_val = 'Failure'
            logger.error(
                f'Something went wrong while updating the node\'s hostname: {result.status_code}, {result.content}')

        ip_lines = self.__exec_command('ip a | grep -w "inet"').read().decode('utf-8').strip()
        # parsing the private ips.
        for ip_line in ip_lines.splitlines():
            specific_ip = ip_line.split()[1].split('/')[0]
            if specific_ip.startswith('127.0') or 'docker' in ip_line:
                continue

            ips.append(specific_ip)

        result = self.request_remote_plugin(f'node/{self.node_id}', method='post', json={'key': 'ips',
                                                                                         'value': ips})
        if result.status_code != 200:
            logger.error(
                f'Something went wrong while updating the node\'s ips: {result.status_code}, {result.content}')
            return_val = 'Failure'
        return return_val

    def __exec_system_command(self, cmd: str) -> paramiko.ChannelFile:
        """
        Executes an axonius_system.py command
        PWD is the cortex directory
        :param cmd: command to execute
        :return: stdout
        """
        return self.__exec_command(f'cd cortex; ./pyrun.sh devops/axonius_system.py {cmd}')

    @retry(wait_fixed=10000,
           stop_max_delay=60000,
           retry_on_exception=retry_if_parallelism_maxed)
    def __exec_command(self, cmd: str) -> paramiko.ChannelFile:
        """
        Executes a command on the host using ssh
        :param cmd: command to execute
        :return: stdout
        """
        _, stdout, _ = self.__host_ssh.exec_command(cmd)
        return stdout

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

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.NotRunning
