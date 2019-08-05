import logging
import socket
import struct
from typing import Iterable, Dict

import paramiko
from retrying import retry

from axonius.utils.threading import LazyMultiLocker
from axonius.mixins.triggerable import Triggerable, RunIdentifier
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.plugin_base import PluginBase
from axonius.utils.files import get_local_config_file

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
        self.__adapters = get_adapter_names_mappings(self.__exec_command('ls'))
        assert len(self.__adapters) > 100, f'Can not get all adapters mappings, got just {self.__adapters}'

        logger.info('Got SSH and adapter names mapping')
        logger.debug(self.__adapters)

        self.__lazy_locker = LazyMultiLocker()

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

    @retry(wait_fixed=10000,
           stop_max_delay=60000,
           retry_on_exception=retry_if_parallelism_maxed)
    def __exec_command(self, cmd: str) -> paramiko.ChannelFile:
        """
        Executes an axonius_system.py command
        PWD is the cortex directory
        :param cmd: command to execute
        :return: stdout
        """
        _, stdout, _ = self.__host_ssh.exec_command(f'cd cortex; ./pyrun.sh devops/axonius_system.py {cmd}')
        return stdout

    def start_adapter(self, adapter_name: str):
        """
        (Re) Starts an adapter
        :param adapter_name: the adapter name to start, e.g. 'ad', 'aws' or 'qualys'
        :return: the output of the command
        """
        return log_file_and_return(self.__exec_command(f'adapter {adapter_name} up --restart --prod'))

    def stop_adapter(self, adapter_name: str):
        """
        Stops an adapter
        :param adapter_name: the adapter name to stop, e.g. 'ad', 'aws' or 'qualys'
        :return: the output of the command
        """
        return log_file_and_return(self.__exec_command(f'adapter {adapter_name} down'))

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.NotRunning
