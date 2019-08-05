import json
import subprocess
import logging

from axonius.utils.parsing import get_exception_string
from axonius.adapter_exceptions import GetDevicesError

logger = logging.getLogger(f'axonius.{__name__}')

WMI_NAMESPACE = "root\\virtualization\\v2"

# Note! After this time the process will be terminated. We shouldn't ever terminate a process while it runs,
# In case its the execution we might leave some files on the target machine which is a bad idea.
# For exactly this reason we have another mechanism to reject execution promises on the execution-requester side.
# This value should be for times we are really really sure there is a problem.
MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS = 60 * 60


class HyperVConnection(object):
    def __init__(self, host, user_name, password, wmi_util_path, python_27_path):
        """ Initializes a connection to a hyper-v server using wmi :-(

        :param str host: server address
        :param str user_name: username to connect to that server
        :param str password: password to connect to that server
        """
        self.host = host
        self.user_name = user_name
        self.password = password
        self._wmi_util_path = wmi_util_path
        self._python_27_path = python_27_path

        self.connect()

    def connect(self):
        commands = [
            {"type": "query", "args": ["select * from Msvm_ComputerSystem where Caption=\"Virtual Machine\""]},
        ]

        output = self._execute_wmi_command(commands)
        if output[0]["status"] != 'ok':
            raise ValueError(f"Error in connect, got output {output}")

    def _get_basic_wmi_smb_command(self):
        """ Function for formatting the base wmiquery command.

        :return list: The basic command
        """
        # Putting the file using wmi_smb_path.
        client_username = self.user_name
        if '\\' in client_username:
            domain_name, user_name = client_username.split('\\')
        elif '/' in client_username:
            domain_name, user_name = client_username.split('/')
        else:
            # This is a legitimate flow. Do not try to build the domain name from the configurations.
            domain_name, user_name = '', client_username
        return [self._python_27_path, self._wmi_util_path, domain_name, user_name, self.password, self.host,
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
            err_log = "Execution Timeout after {4} seconds!! command {0}, stdout: {1}, " \
                      "stderr: {2}, exception: {3}".format(commands,
                                                           str(command_stdout),
                                                           str(command_stderr),
                                                           get_exception_string(),
                                                           MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS)
            logger.error(err_log)
            raise ValueError(err_log)
        except subprocess.SubprocessError:
            # This is a base class for all the rest of subprocess excpetions.
            err_log = f"General Execution error! command {commands}, exception: {get_exception_string()}"
            logger.error(err_log)
            raise ValueError(err_log)

        if subprocess_handle.returncode != 0:
            err_log = f"Execution Error! command {commands} returned returncode " \
                      f"{subprocess_handle.returncode}, stdout {command_stdout} stderr {command_stderr}"
            logger.error(err_log)
            raise ValueError(err_log)

        commands_json = json.loads(command_stdout.strip())
        if len(commands_json) != len(commands):
            raise ValueError(
                f"unexpected result, expected {len(commands)} results to come back but got {len(commands_json)}")

        return commands_json

    def get_devices(self):
        commands = [
            {"type": "query", "args": ["select * from Msvm_ComputerSystem where Caption=\"Virtual Machine\""]},
            {"type": "query", "args": ["select * from Msvm_SyntheticEthernetPort"]},
            {"type": "query", "args": ["select * from Msvm_DiskDrive"]},
            {"type": "query", "args": ["select * from Msvm_Processor"]},
            {"type": "query", "args": ["select * from Msvm_GuestNetworkAdapterConfiguration"]}
        ]

        wmi_data = self._execute_wmi_command(commands)

        try:
            vms_data = wmi_data[0]['data'] if wmi_data[0]['status'] == 'ok' else []
            for current_vm in vms_data:
                try:
                    switch_data = wmi_data[1]['data'] if wmi_data[1]['status'] == 'ok' else []
                    current_vm[u'Switches'] = []
                    for current_switch in switch_data:
                        if current_switch['SystemName'] == current_vm['Name']:
                            current_vm[u'Switches'].append(current_switch)
                except Exception:
                    logger.exception('No switches information returned from wmi (no MAC addresses).')

                try:
                    disk_drive_data = wmi_data[2]['data'] if wmi_data[2]['status'] == 'ok' else []
                    current_vm[u'DiskDrives'] = []
                    for current_disk in disk_drive_data:
                        if current_disk['SystemName'] == current_vm['Name']:
                            current_vm[u'DiskDrives'].append(current_disk)
                except Exception:
                    logger.exception('No hard drive information returned from wmi.')

                try:
                    cpu_data = wmi_data[3]['data'] if wmi_data[3]['status'] == 'ok' else []
                    current_vm[u'Cpus'] = []
                    for current_cpu in cpu_data:
                        if current_cpu['SystemName'] == current_vm['Name']:
                            current_vm[u'Cpus'].append(current_cpu)
                except Exception:
                    logger.exception('No cpu information returned from wmi.')

                try:
                    network_data = wmi_data[4]['data'] if wmi_data[4]['status'] == 'ok' else []
                    current_vm[u'Networks'] = []
                    for current_network in network_data:
                        if current_vm['Name'] in current_network['InstanceID']:
                            current_vm[u'Networks'].append(current_network)
                except Exception:
                    logger.exception('No network information returned from wmi (IP addresses.')
        except Exception:
            logger.exception('WMI returned no vm information.')
            raise GetDevicesError('WMI returned no vm information.')

        return vms_data
