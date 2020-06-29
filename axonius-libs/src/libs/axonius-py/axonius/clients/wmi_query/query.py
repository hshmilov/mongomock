import json
import logging
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum, auto
from typing import Dict, Iterator, List, Tuple, Union, Optional

from axonius.utils.parsing import get_exception_string

# pylint: disable=W0105
'''
Wmi util for query/execute code on windows machines.
Notes:
    - Hostname validation:
        If an hostname is given in the devices list, hostname will be checked against the machine
        using wmi hostname query.
        if the hostname does'nt match, the rest of the execution will be stopped
        and WmiHostnameValidationException will be raised.
'''

MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS = 60 * 60 * 1  # 1 hour
MAX_THREAD_WORKERS = 5
HOSTNAME_VALIDATION_QUERY = 'select Name from Win32_ComputerSystem'
NAMESPACE = '//./root/cimv2'
logger = logging.getLogger(f'axonius.{__name__}')

WmiResults = Union[dict, Exception]


class WmiStatus(Enum):
    Failure = auto()
    Success = 'ok'


class QueryType(Enum):
    QUERY = 'query'
    PM = 'pm'
    PMONLINE = 'pmonline'


class WmiCommands(Enum):
    PUT_FILE = 'putfilefromdisk'
    SHELL = 'shell'


class WmiQueryException(Exception):
    pass


class WmiHostnameValidationException(Exception):
    pass


def run_process(args, timeout: int) -> Tuple[int, str, str]:
    """
    Run subprocess and get the output
    :param args: subprocess args
    :param timeout: subprocess exec timeout
    :return: process output data: exitcode, stdout, stderror
    """
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdoutdata, stderrdata = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        stdoutdata, stderrdata = process.communicate()
        err_log = f'Execution Timeout after {timeout} seconds!! stdout: {stdoutdata}, ' \
                  f'stderr: {stderrdata}, exception: {get_exception_string()}'
        raise ValueError(err_log)
    except Exception:
        # This is a base class for all the rest of subprocess excpetions.
        err_log = f'General Execution error! command, exception: {get_exception_string()}'
        raise ValueError(err_log)

    return process.returncode, stdoutdata, stderrdata


def handle_wmi_response(retcode: int, command_stdout: bytes, command_stderr: bytes) -> dict:
    """
    Check for wmi subprocess response status
    :param retcode: subprocess return code
    :param command_stdout: subprocess stdout
    :param command_stderr: subprocess stderr
    :raises ValueError: bad response from wmi subprocess
    :return: wmi response dict
    :raises: WmiQueryException on parse error.
    """
    logger.info(f'retcode {retcode}')
    logger.debug(f'command_stdout {command_stdout}')
    logger.debug(f'command_stderr {command_stderr}')
    if retcode == 0 and command_stdout is not None:
        try:
            response = json.loads(command_stdout.strip())
            return response
        except Exception:
            err_log = f'Json parse Error! command returned returncode ' \
                      f'{retcode}, stdout {command_stdout} stderr {command_stderr}'
            logger.error(err_log)
            raise WmiQueryException(err_log)

    if 'Could not connect: [Errno 111] Connection refused' in command_stdout.decode('utf-8') \
            or 'Could not connect: [Errno 111] Connection refused' in command_stderr.decode('utf-8'):
        err_log = 'Error - Connection Refused!'
    else:
        err_log = f'Execution Error! command returned returncode ' \
                  f'{retcode}, stdout {command_stdout} stderr {command_stderr}'
    logger.error(err_log)
    raise WmiQueryException(err_log)


def get_basic_wmi_smb_command(python_27_path: str, wmi_smb_path: str,
                              ip: str, username: str, password: str) -> list:
    """ Function for formatting the base wmiqery command.
    :param python_27_path: python 2.7 path.
    :param wmi_smb_path: wmi_smb_path file path.
    :param ip: device ip
    :param username: device username
    :param password: device password
    :return string: The basic command
    """
    if '\\' in username:
        domain_name, user_name = username.split('\\')
    else:
        # This is a legitimate flow. Do not try to build the domain name from the configurations.
        domain_name, user_name = '', username
    abs_wmi_smb_path = os.path.abspath(os.path.join(os.path.dirname(__file__), wmi_smb_path))
    return [python_27_path, abs_wmi_smb_path, domain_name, user_name, password, ip,
            NAMESPACE]


def execute_shell(python_27_path: str, wmi_smb_path: str,
                  username: str, password: str, devices_ips: List[Tuple[str, str]],
                  shell_commands,
                  extra_files: Optional[dict] = None) -> Iterator[WmiResults]:
    """
    Shell commands is a dict of which keys are operation systems and values are lists of cmd commands.
    The commands will be run *in parallel* and not consequently.
    :param devices_ips: list of devices ip,hostname to run wmi commands on,
    if hostname exists ip is validated against it.
    :param python_27_path: python 2.7 path.
    :param wmi_smb_path: wmi_smb_path file path.
    :param username: device username
    :param password: device password
    :param shell_commands: e.g. {"Windows": ["dir", "ping google.com"]}
    :param extra_files: extra files to upload (a list of paths)
    :return:
    """

    shell_command_windows = shell_commands.get('Windows')
    if shell_command_windows is None:
        raise WmiQueryException('No Windows command supplied')

    # Since wmi_smb_runner runs commands in parallel we first have to upload files then run commands.
    upload_files_commands_list = []
    for file_name, file_path in (extra_files or {}).items():
        file_name = file_name.split('/')[-1].split('\\')[-1]
        upload_files_commands_list.append({
            'type': WmiCommands.PUT_FILE.value,
            'args': [file_path, file_name]
        })

    if upload_files_commands_list:
        for res in run_wmi_smb_on_devices(python_27_path, wmi_smb_path, username, password, upload_files_commands_list,
                                          devices_ips):
            # yield the results on upload exception.
            if isinstance(res, Exception):
                yield res

    commands_list = [{
        'type': WmiCommands.SHELL.value,
        'args': [command]
    } for command in shell_command_windows]
    for res in run_wmi_smb_on_devices(python_27_path, wmi_smb_path, username, password, commands_list,
                                      devices_ips):
        yield res


def validate_hostname(python_27_path: str, wmi_smb_path: str,
                      username: str, password: str, ip: str, hostname_to_validate,
                      timeout: int = MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS) -> bool:
    """
    In some scenarios, we think we run code on device X while the dns is incorrect and it makes us
    run code on device Y which has the same ip. That is why we append hostname query.
    if the hostname returns, we see if the hostname we know this machine has is the same as what returned.
    :param python_27_path: python 2.7 path.
    :param wmi_smb_path: wmi_smb_path file path.
    :param username: device username
    :param password: device password
    :param ip: ip of device
    :param hostname_to_validate: hostname to be validated against the device
    :param timeout: command timeout
    :return: True if validated, otherwise false.
    """
    # Get the validation wmi command
    hostname_validation_command = {
        'type': QueryType.QUERY.value,
        'args': [HOSTNAME_VALIDATION_QUERY]
    }
    command = get_basic_wmi_smb_command(python_27_path, wmi_smb_path, ip, username, password) + \
        [json.dumps([hostname_validation_command])]
    logger.debug(f'running wmi validation for {ip}')
    ret, stdout, stderr = run_process(command, timeout)
    # Parse validation command output
    product = handle_wmi_response(ret, stdout, stderr)
    hostname_answer = product[0]
    # Validate
    if hostname_answer['status'] == 'ok':
        hostname_on_device = hostname_answer['data'][0].get('Name')
        if hostname_on_device is not None and hostname_on_device != '' and hostname_to_validate != '':
            hostname_on_device = hostname_on_device.lower()
            hostname_to_validate = hostname_to_validate.lower()
            if not (hostname_on_device.startswith(hostname_to_validate) or
                    hostname_to_validate.startswith(hostname_on_device)):
                return False
    return True


def execute_wmi_smb(python_27_path: str, wmi_smb_path: str,
                    username: str, password: str, wmi_smb_commands: List[Dict], ip: str, hostname_to_validate: str,
                    timeout) -> Dict:
    """
    executes a list of wmi + smb possible queries. (look at wmi_smb_runner.py)
    :param python_27_path: python 2.7 path.
    :param wmi_smb_path: wmi_smb_path file path.
    :param username: device username
    :param password: device password
    :param ip: ip of device
    :param hostname_to_validate: hostname to be validated against the device
    :param wmi_smb_commands: a list of dicts, each list in the format of wmi_smb_runner.py.
                        e.g. [{"type": "query", "args": ["select * from Win32_Account"]}]
    :param timeout: command timeout
    :return: axonius-execution result.
    :raises: WmiQueryException on running error, WmiHostnameValidationException on host validation error.
    """
    if not wmi_smb_commands:
        raise WmiQueryException('No WMI/SMB queries/commands list supplied')

    # Due to a problem in impacket (look at wmi_smb_runner.py) we cannot query for wmi + rpc objects
    # in the same run. will be fixed in AX-1384
    hostname_validation = True
    for command in wmi_smb_commands:
        if command['type'].lower() in [QueryType.PM.value, QueryType.PMONLINE.value]:
            hostname_validation = False

    # validate hostname
    if hostname_to_validate and hostname_validation:
        try:
            if not validate_hostname(python_27_path, wmi_smb_path, username, password,
                                     ip, hostname_to_validate, timeout):
                raise WmiHostnameValidationException(f'Hostname Validation Error! {hostname_to_validate} is not {ip}')
        except WmiHostnameValidationException as e:
            raise e
        except Exception:
            logger.exception(f'Error validating hostname: {hostname_to_validate} against {ip}')

    # run commands
    command = get_basic_wmi_smb_command(python_27_path, wmi_smb_path, ip, username, password) + \
        [json.dumps(wmi_smb_commands)]
    ret, stdout, stderr = run_process(command, timeout)
    product = handle_wmi_response(ret, stdout, stderr)

    # Some more validity check
    if len(product) != len(wmi_smb_commands):
        err_log = f'Error, needed to run {wmi_smb_commands} and expected the same length in return ' \
                  f'but got {product}'
        raise WmiQueryException(err_log)

    # Optimization if all failed
    if all(line['status'] != 'ok' for line in product):
        return product
    # If we got here that means the the command executed successfully
    return product


def run_wmi_smb_on_devices(python_27_path: str, wmi_smb_path: str,
                           username: str, password: str, wmi_smb_commands: List[Dict],
                           devices_ips: List[Tuple[str, str]],
                           timeout: int = MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS,
                           max_workers=MAX_THREAD_WORKERS) -> Iterator[WmiResults]:
    """
    executes a list of wmi + smb possible queries. (look at wmi_smb_runner.py)
    :param timeout: command timeout
    :param devices_ips: devices ips to run wmi commands on,
        Tuple of (ip, hostname_to_validate_against_that_ip).
        If hostname_to_validate is None, there will be not validation.
    :param max_workers: max parallel threads for running queries
    :param python_27_path: python 2.7 path.
    :param wmi_smb_path: wmi_smb_path file path.
    :param username: device username
    :param password: device password
    :param wmi_smb_commands: a list of dicts, each list in the format of wmi_smb_runner.py.
                        e.g. [{"type": "query", "args": ["select * from Win32_Account"]}]
    :return: wmi query results.
    """
    if not wmi_smb_commands:
        raise WmiQueryException('No WMI/SMB queries/commands list supplied')

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(execute_wmi_smb, python_27_path, wmi_smb_path, username, password, wmi_smb_commands, ip,
                            hostname, timeout): ip for ip, hostname in devices_ips}
        for future in as_completed(futures):
            try:
                yield future.result()
            except Exception as e:
                yield e
