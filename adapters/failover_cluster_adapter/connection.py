import json
import logging
import subprocess

from failover_cluster_adapter.consts import MAX_SUBPROCESS_TIMEOUT, WMI_NAMESPACE
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import get_exception_string
from axonius.utils.json import from_json

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
        # Get-ClusterNode module and its version number. A string will
        # be returned, but JSON indicates a successful execution.
        command = f'powershell.exe -c (Get-Command Get-ClusterNode).Name + " " + ' \
                  f'(Get-Command Get-ClusterNode).Version.Major + " " + ' \
                  f'(Get-Command Get-ClusterNode).Version.Minor'

        commands = [{'type': 'shell', 'args': [command]}]

        try:
            response = self._execute_wmi_command(commands)
            logger.debug(f'Initial Connect: {response}')

            if response[0]['status'] != 'ok':
                message = f'Error in connect, got output {response}'
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

    # pylint: disable=line-too-long
    def _device_get(self):
        """
        Cluster Properties:
            https://docs.microsoft.com/en-us/previous-versions/windows/desktop/mscs/cluster-common-properties
        Node Properties:
            https://docs.microsoft.com/en-us/previous-versions/windows/desktop/mscs/node-common-properties

        Failover Cluster Powershell Cmdlets:
            https://docs.microsoft.com/en-us/powershell/module/failoverclusters/?view=win10-ps
        Get-Cluster:
            https://docs.microsoft.com/en-us/powershell/module/failoverclusters/get-cluster?view=win10-ps
        Get-ClusterNode:
            https://docs.microsoft.com/en-us/powershell/module/failoverclusters/Get-ClusterNode?view=win10-ps
        Get-ClusterResource:
            https://docs.microsoft.com/en-us/powershell/module/failoverclusters/get-clusterresource?view=win10-ps

        This was an example I found on the web, but I don't see how it might work:
        https://cloudcompanyapps.com/2019/03/07/powershell-get-all-running-vms-in-a-failover-cluster/
            $clusterNodes = Get-ClusterNode;
            ForEach($item in $clusterNodes) {Get-VM -ComputerName $item.Name}

        if the command below doesn't work, you can do this to get the node names:
        Get-ClusterNode --Cluster devhv01

        more information/ideas:
        https://stackoverflow.com/questions/21409249/powershell-how-to-return-all-the-vms-in-a-hyper-v-cluster
        """
        commands = list()
        try:
            # get a list of dicts in the format of [{'Name': 'node_name'},...]
            get_node_list = f'powershell.exe -c Get-ClusterNode ^| Select Name ^| ConvertTo-Json'
            commands = [{'type': 'shell', 'args': [get_node_list]}]

            node_list_response = self._execute_wmi_command(commands)

            if node_list_response[0]['status'] != 'ok':
                message = f'Failed to run Get-ClusterNode command through ' \
                          f'WMI/PowerShell: Got {node_list_response}'
                logger.error(message)
                return

            nodes_list_data = node_list_response[0].get('data')
            if not nodes_list_data:
                message = f'Malformed raw data. Expected a list, got ' \
                          f'{type(nodes_list_data)}: {str(nodes_list_data)}'
                logger.warning(message)
                raise ValueError(message)

            nodes = from_json(nodes_list_data)

            # use the node name to pull data about that node
            for node in nodes:
                node_name = node.get('Name')
                if not isinstance(node_name, str):
                    logger.warning(f'Malformed node name. Expected a string, '
                                   f'got {type(node_name)}: {str(node_name)}')
                    continue

                get_node_resources = f'powershell.exe -c Get-ClusterNode -Name {node_name} ^| Get-ClusterResource ^| ConvertTo-Json'
                commands = [{'type': 'shell', 'args': [get_node_resources]}]

                logger.debug(f'Fetching {node_name}')
                node_response = self._execute_wmi_command(commands)

                if node_response[0]['status'] != 'ok':
                    message = f'Failed to run Get-ClusterNode command through ' \
                              f'WMI/PowerShell: Got {node_response}'
                    logger.error(message)
                    return

                raw_node_data = node_response[0].get('data')
                if not raw_node_data:
                    message = f'Malformed raw node data from Get-ClusterNade: ' \
                              f'{str(node_response)}'
                    logger.warning(message)
                    continue

                device_data_raw = from_json(raw_node_data)

                # data is the only item in a list, so yield only the dict
                yield device_data_raw[0]

        except Exception:
            logger.exception(f'Invalid request made while paginating '
                             f'devices: {commands}')
            raise

    def get_device_list(self):
        try:
            yield from self._device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
