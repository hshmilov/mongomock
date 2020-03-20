import json
import subprocess
import logging

from axonius.utils.json import from_json

from axonius.utils.parsing import get_exception_string
from axonius.adapter_exceptions import GetDevicesError

logger = logging.getLogger(f'axonius.{__name__}')

WMI_NAMESPACE = '//./root/cimv2'

# Note! After this time the process will be terminated. We shouldn't ever terminate a process while it runs,
# In case its the execution we might leave some files on the target machine which is a bad idea.
# For exactly this reason we have another mechanism to reject execution promises on the execution-requester side.
# This value should be for times we are really really sure there is a problem.
MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS = 60 * 60


class WsusWmiConnection:
    def __init__(self,
                 host,
                 user_name,
                 password,
                 wmi_util_path,
                 python_27_path):
        """
        Create a WMI connection to WSUS server
        :param host: WSUS server host
        :param user_name: [Domain/||Domain\\]username to connect with
        :param password: Password for connection
        :param wmi_util_path: Path to wmi util file
        :param python_27_path: Path to python27
        """
        self.host = host
        self._user_name = user_name
        self._password = password
        self._wmi_util_path = wmi_util_path
        self._python_27_path = python_27_path

        self.connect()

    @staticmethod
    def _prepare_command(command):  # , output_file=None, working_dir=None):
        # output_file = output_file or self.__output_file
        # working_dir = working_dir or self.__cwd
        return {
            'type': 'shell',
            'args': [
                command,
                # output_file,
                # working_dir
            ]
        }

    def connect(self):
        command = [self._prepare_command('Get-WsusServer')]
        output = self._execute_wmi_command(command)
        if output[0]['status'] != 'ok':
            raise ValueError(f'Error in connect, got output {output}')

    def _get_basic_wmi_smb_command(self):
        """ Function for formatting the base wmiquery command.

        :return list: The basic command
        """
        # Putting the file using wmi_smb_path.
        client_username = self._user_name
        if '\\' in client_username:
            domain_name, user_name = client_username.split('\\')
        elif '/' in client_username:
            domain_name, user_name = client_username.split('/')
        else:
            # This is a legitimate flow. Do not try to build the domain name from the configurations.
            domain_name, user_name = '', client_username
        return [self._python_27_path, self._wmi_util_path, domain_name, user_name, self._password, self.host,
                WMI_NAMESPACE]

    def _execute_wmi_command(self, commands):
        subprocess_handle = subprocess.Popen(self._get_basic_wmi_smb_command() + [json.dumps(commands)],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)

        try:
            command_stdout, command_stderr = subprocess_handle.communicate(
                timeout=MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS)
        except subprocess.TimeoutExpired:
            # The child process is not killed if the timeout expires, so in order to cleanup properly a well-behaved
            # application should kill the child process and finish communication (from python documentation)
            subprocess_handle.kill()
            command_stdout, command_stderr = subprocess_handle.communicate()
            err_log = 'Execution Timeout after {4} seconds!! command {0}, stdout: {1}, ' \
                      'stderr: {2}, exception: {3}'.format(commands,
                                                           str(command_stdout),
                                                           str(command_stderr),
                                                           get_exception_string(),
                                                           MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS)
            logger.error(err_log)
            raise ValueError(err_log)
        except subprocess.SubprocessError:
            # This is a base class for all the rest of subprocess excpetions.
            err_log = f'General Execution error! command {commands}, exception: {get_exception_string()}'
            logger.error(err_log)
            raise ValueError(err_log)

        if subprocess_handle.returncode != 0:
            err_log = f'Execution Error! command {commands} returned returncode ' \
                      f'{subprocess_handle.returncode}, stdout {command_stdout} stderr {command_stderr}'
            logger.error(err_log)
            raise ValueError(err_log)

        commands_json = json.loads(command_stdout.strip())
        if len(commands_json) != len(commands):
            raise ValueError(
                f'unexpected result, expected {len(commands)} results to come back but got {len(commands_json)}')

        return commands_json

    def get_devices(self):
        command_text = 'powershell.exe -c ConvertTo-Json((Get-WsusServer).GetComputerTargets())'
        commands = [self._prepare_command(command_text)]

        output = self._execute_wmi_command(commands)
        if output[0]['status'] != 'ok':
            message = f'Failed to get devices through WMI/PowerShell: Got {output}'
            logger.error(message)
            raise GetDevicesError(message)
        try:
            result_data = from_json(output[0]['data'])
        except Exception:
            message = f'Failed to parse data from {output}!'
            logger.exception(message)
            # raise GetDevicesError(message)
        else:
            if result_data:
                yield from result_data
