import json
import logging
import subprocess

from failover_cluster_adapter.consts import MAX_SUBPROCESS_TIMEOUT, WMI_NAMESPACE
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import get_exception_string

logger = logging.getLogger(f'axonius.{__name__}')


class FailoverClusterConnection(RESTConnection):
    """ REST client for FailoverCluster adapter """

    def __init__(self,
                 wmi_util_path: str,
                 python_path: str,
                 *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._wmi_util_path = wmi_util_path
        self._python_path = python_path

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        # this command checks for the presence of the required
        # Get-ClusterNode module. A string will be returned, but JSON
        # indicates a successful execution.
        command = f'powershell.exe -c Get-Command Get-ClusterNode ' \
                  f'-ErrorAction Stop | ConvertTo-Json'
        commands = [{'type': 'query', 'args': [command]}]
        try:
            response = self._execute_wmi_command(commands)
            logger.debug(f'Initial Connect: {response}')
            if not isinstance(response, str):
                raise ValueError(f'Got a non-string response: {response}')

            if not response.startswith('{'):
                message = f'Get-ClusterNode is not installed: {response}'
                logger.warning(message)
                raise ValueError(message)

        except Exception as err:
            raise ValueError(f'Error: Invalid response from server, '
                             f'please check domain or credentials: {err}')

    def _get_basic_wmi_smb_command(self):
        """
        Function for formatting the base wmiquery command.

        :return list: The basic command
        """
        # Putting the file using wmi_smb_path.
        client_username = self._username
        if '\\' in client_username:
            domain_name, user_name = client_username.split('\\')
        elif '/' in client_username:
            domain_name, user_name = client_username.split('/')
        else:
            # This is a legitimate flow. Do not try to build the domain name
            # from the configurations.
            domain_name, user_name = '', client_username
        return [self._python_path,
                self._wmi_util_path,
                domain_name,
                user_name,
                self._password,
                self._domain,
                WMI_NAMESPACE]

    def _execute_wmi_command(self, commands):
        subprocess_handle = subprocess.Popen(self._get_basic_wmi_smb_command() +
                                             [json.dumps(commands)],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)

        command_stdout = b''
        command_stderr = b''

        try:
            command_stdout, command_stderr = subprocess_handle.communicate(
                timeout=MAX_SUBPROCESS_TIMEOUT)
        except subprocess.TimeoutExpired:
            # The child process is not killed if the timeout expires, so in
            # order to cleanup properly a well-behaved application should kill
            # the child process and finish communication (from python
            # documentation)
            subprocess_handle.kill()
            command_stdout, command_stderr = subprocess_handle.communicate()

            err = f'Execution Timeout at {MAX_SUBPROCESS_TIMEOUT} seconds! ' \
                  f'command {commands}, ' \
                  f'stdout: {str(command_stdout)}, ' \
                  f'stderr: {str(command_stderr)}, ' \
                  f'exception: {get_exception_string()}'
            logger.error(err)
            raise ValueError(err)
        except subprocess.SubprocessError:
            err = f'General Execution error: {commands} exception: ' \
                  f'{get_exception_string()}'
            logger.error(err)
            raise ValueError(err)

        if subprocess_handle.returncode != 0:
            err = f'Execution Error! command {commands} returned ' \
                  f'returncode {subprocess_handle.returncode}, ' \
                  f'stdout {command_stdout} ' \
                  f'stderr {command_stderr}'
            logger.error(err)
            raise ValueError(err)

        commands_json = json.loads(command_stdout.strip())
        if len(commands_json) != len(commands):
            raise ValueError(f'unexpected result, expected {len(commands)} '
                             f'results to come back but got '
                             f'{len(commands_json)}')

        return commands_json

    def _paginated_device_get(self):
        """
        Pure Powershell:
            $clusterNodes = Get-ClusterNode;
            ForEach($item in $clusterNodes)
            {Get-VM -ComputerName $item.Name; }
        :return:
        """
        try:
            command = f'powershell.exe -c Get-ClusterNode | ConvertTo-Json'
            commands = [{'type': 'query', 'args': [command]}]

            response = self._execute_wmi_command(commands)
            logger.info(f'paginated response (single cluster): '
                        f'{response}, default')
            yield response, self._domain

        except Exception:
            logger.exception(f'Invalid request made while paginating '
                             f'devices: {commands}')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
