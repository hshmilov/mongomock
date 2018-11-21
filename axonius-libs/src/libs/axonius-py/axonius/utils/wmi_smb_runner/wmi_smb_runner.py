"""
The following file implements wmi queries. It uses python2 and the impacket external library.
Since we usually use python3, it is intended to be run as a subprocess.

Note! We only support username & password right now. Hashes, nopass, kerberos auth, aes-key or rpc-auth level
were ommited. To see how to use them, see "wmiexec.py" or "wmiquery.py" in impacket/examples.

The following also have three advantages:
1. It can execute multiple queries/methods on the same connection.
2. It minimizes the size by reducing not important info we get from impacket.
3. It handles failing commands to return the rest of the commands if we have multiple(1).
"""

import sys
import os
import ntpath
import json
import time
import socket
import threading
import base64

from impacket.dcerpc.v5.dtypes import NULL
from impacket.dcerpc.v5.dcom import wmi
from impacket.dcerpc.v5.dcomrt import DCOMConnection
from impacket.dcerpc.v5.rpcrt import RPC_C_AUTHN_LEVEL_PKT_PRIVACY, RPC_C_AUTHN_LEVEL_PKT_INTEGRITY, \
    RPC_C_AUTHN_LEVEL_NONE
from impacket.smbconnection import SMBConnection, SessionError
from multiprocessing.pool import ThreadPool
from retrying import retry
from contextlib import contextmanager
from handlers.remotewua import RemoteWUAHandler


MAX_NUM_OF_CONSECUTIVE_QUERY_FAILURES = 2    # Maximum number of times we can fail with not even one success
MAX_NUM_OF_GET_DEFAULT_WORKING_DIRECTORY = 3    # Maximum times we try to get the default working directory.
MAX_NUM_OF_TRIES_PER_CONNECT = 2    # Maximum number of tries to connect.
TIME_TO_REST_BETWEEN_CONNECT_RETRY = 3 * 1000   # 3 seconds.
SMB_CONNECTION_TIMEOUT = 60 * 30  # 30 min timeout. Change that for even larger files
MAX_SHARING_VIOLATION_TIMES = 5  # Maximum legitimate error we can have in smb connection
# The maximum amount of seconds we wait for the created shell process to finish before bailing out
MAX_TIMEOUT_FOR_CREATED_SHELL_PROCESS = 60 * 5

# each request gets this amount of seconds to return. If one returns, the timer of all the rest resets.
TIMER_RESET_FOR_EACH_REQUEST_IN_SECONDS = 180
TIME_TO_SLEEP_BETWEEN_EACH_ANSWER_CHECK_IN_SECONDS = 2

# A writeable share from which we will be grabbing shell output. TODO: Check IPC$
# Note! ADMIN$ usually points to %windir% so we can have relative paths across the entire code.
# If you change it, change all usages across the entire code!
DEFAULT_SHARE = "ADMIN$"

# The name of the directory we will be creating, in which all of our internal files reside
FILES_DIRECTORY = "axonius"

__global_counter = 0
__global_counter_lock = threading.Lock()


def find_shared_readonly_files():
    """
    Returns the shared readonly files directory of the project.
    We can run from tests, But we can also run from within container, so we have to identify it.
    :return: the root directory.
    """
    current_dir = os.path.abspath(os.path.dirname(__file__))
    for i in range(20):
        candidate = os.path.join(current_dir, "shared_readonly_files")
        # Of course this isn't the best thing to do, but at least we will fail tests immediately if this condition
        # is met and is incorrect.
        if os.path.exists(candidate):
            return candidate

        current_dir = os.path.join(current_dir, "..")

    raise ValueError, "Can't find shared readonly files dir"


SHARED_READONLY_FILES = find_shared_readonly_files()

AXPM_BINARY_LOCATION = os.path.abspath(
    os.path.join(SHARED_READONLY_FILES, "AXPM", "AXPM.exe"))

WSUSSCN2_BINARY_LOCATION = os.path.abspath(
    os.path.join(SHARED_READONLY_FILES, "AXPM", "wsusscn2", "wsusscn2.cab"))

AXR_BINARY_LOCATION = os.path.abspath(
    os.path.join(SHARED_READONLY_FILES, "AXR", "axr.exe"))

AXR_CONFIG_BINARY_LOCATION = os.path.abspath(
    os.path.join(SHARED_READONLY_FILES, "AXR", "axr.exe.config"))


def get_global_counter():
    global __global_counter
    with __global_counter_lock:
        __global_counter += 1
        return __global_counter - 1


def get_exception_string():
    """
    when inside a catch exception flow, returns a really informative string representing it.
    :return: a string representing the exception.
    """
    exc_type, exc_obj, exc_tb = sys.exc_info()

    ex_str = "Traceback (most recent call last):\n"
    while exc_tb is not None:
        ex_str = ex_str + "  File {0}, line {1}, in {2}\n".format(
            exc_tb.tb_frame.f_code.co_filename,
            exc_tb.tb_lineno,
            exc_tb.tb_frame.f_code.co_name)

        exc_tb = exc_tb.tb_next

    ex_str = ex_str + "{0}:{1}".format(exc_type, exc_obj)
    return ex_str


class WmiSmbRunner(object):
    """
    Runs WMI queries and methods on a given host.
    """
    did_create_files_directory = False
    default_working_directory = None

    def __init__(self, address, username, password, domain='', dc_ip=None, lmhash='', namespace="//./root/cimv2", nthash='', aes_key=None,
                 use_kerberos=False, rpc_auth_level="default"):
        """
        Initializes a WmiSmbRunner object.
        :param address: the ip of the host we are connecting to.
        :param username: The username we use.
        :param password: The password of that username.
        :param domain: The domain we are connecting to. This is usually needed, but not always.
        :param dc_ip: The ip of the dc. Optional.
        :param lmhash: part of NTLM Hashes. optional auth method.
        :param nthash: part of NTLM Hashes. optional auth method.
        :param aes_key: aes key for kerberos auth. optional auth method.
        :param use_kerberos: Use Kerberos authentication. Grabs credentials from ccache file (KRB5CCNAME)
                             based on target parameters. If valid credentials cannot be found, it will use the
                             credentials given in the initialization.
        :param rpc_auth_level: defaults to "default", but can be integrity (RPC_C_AUTHN_LEVEL_PKT_INTEGRITY) or
                               privacy (RPC_C_AUTHN_LEVEL_PKT_PRIVACY).
        :param namespace: the wmi namespace.
        """

        self.address = socket.gethostbyname(address)    # This doesn't work otherwise, if given a hostname
        self.username = username
        self.password = password
        self.domain = domain
        self.dc_ip = dc_ip
        self.lmhash = lmhash
        self.nthash = nthash
        self.aes_key = aes_key
        self.use_kerberos = use_kerberos
        self.rpc_auth_level = rpc_auth_level
        self.dcom = None
        self.__rpc_creation_lock = threading.Lock()
        self.__namespace = namespace
        self.__smb_connection_creation_lock = threading.RLock()
        self.__is_smb_connection_initialized = False
        self.__remotewua = None
        self.__iWbemServices_dict = {}

        if aes_key is not None:
            self.use_kerberos = True

    def __enter__(self):
        self.connect()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.before_close()
        self.close()

    def getfile(self, filepath, share=DEFAULT_SHARE):
        """
        Gets a file.
        :param filepath: the filename, which exists on share.
        :param share: a share to get the file from, e.g. ADMIN$.
        :return: the file
        """

        # Normalize filepath
        filepath = ntpath.normpath(filepath)    # also replaces / with \
        assumed_share, filepath = ntpath.splitdrive(filepath)
        if assumed_share != '':
            share = assumed_share[:-1] + "$"

        class FileReceiver(object):
            """
            Just a helper to receive files from SMB.
            """

            def __init__(self):
                self.contents = ""

            def write_to_contents(self, data):
                self.contents = self.contents + data

        with self.get_smb_connection() as smb_connection:
            sharing_violation_times = 0
            while True:
                try:
                    fr = FileReceiver()
                    smb_connection.getFile(share, filepath, fr.write_to_contents)
                    return fr.contents
                except Exception as e:
                    if str(e).find('STATUS_SHARING_VIOLATION') >= 0:
                        sharing_violation_times = sharing_violation_times + 1
                        if sharing_violation_times > MAX_SHARING_VIOLATION_TIMES:
                            raise
                        # Not finished, let's wait
                        time.sleep(1)
                    else:
                        raise

    def putfile(self, filepath, filecontents, share=DEFAULT_SHARE):
        """
        Puts a file remotely.
        :param filepath: the name of the file.
        :param filecontents: the contents of the file.
        :param share: the share (optional).
        :return:
        """

        # Normalize filepath
        filepath = ntpath.normpath(filepath)  # also replaces / with \
        assumed_share, filepath = ntpath.splitdrive(filepath)
        if assumed_share != '':
            share = assumed_share[:-1] + "$"

        class FileSender(object):
            """
            A helper class for sending files.
            """

            def __init__(self, file_contents):
                self.contents = file_contents
                self.already_sent = 0

            def read(self, size):
                buf = self.contents[self.already_sent:self.already_sent + size]
                self.already_sent += size
                # This is a debug code that is very useful to us, so i'm leaving it here.
                # sys.stderr.write("got size {0}, already sent {1} ({2} mb).\n".format(
                #     size, self.already_sent, self.already_sent / 1024.0 / 1024.0))
                # sys.stderr.flush()
                return buf

        with self.get_smb_connection() as smb_connection:
            sharing_violation_times = 0
            while True:
                try:
                    fs = FileSender(filecontents)
                    smb_connection.putFile(share, filepath, fs.read)
                    return True
                except Exception as e:
                    if str(e).find('STATUS_SHARING_VIOLATION') >= 0:
                        sharing_violation_times = sharing_violation_times + 1
                        if sharing_violation_times > MAX_SHARING_VIOLATION_TIMES:
                            raise
                        # Not finished, let's wait
                        time.sleep(1)
                    else:
                        raise

    def deletefile(self, filepath, share=DEFAULT_SHARE):
        """
        Deletes a file.
        :param filepath: the filepath, which exists on share.
        :param share: a share to get the file from, e.g. ADMIN$.
        :return: the file
        """

        # Normalize filepath
        filepath = ntpath.normpath(filepath)  # also replaces / with \
        assumed_share, filepath = ntpath.splitdrive(filepath)
        if assumed_share != '':
            share = assumed_share[:-1] + "$"

        with self.get_smb_connection() as smb_connection:
            sharing_violation_times = 0
            while True:
                try:
                    smb_connection.deleteFile(share, filepath)
                    break
                except Exception as e:
                    if str(e).find('STATUS_SHARING_VIOLATION') >= 0:
                        sharing_violation_times = sharing_violation_times + 1
                        if sharing_violation_times > MAX_SHARING_VIOLATION_TIMES:
                            raise
                        # Not finished, let's wait
                        time.sleep(1)
                    else:
                        raise

        return True

    def _trydeletefile(self, filepath, share=DEFAULT_SHARE):
        """
        Try to delete the file, if it doesn't work just go on.
        :param filepath: the filpath arg for deletefile
        :param share: the share arg for deletefile
        :return: deletefile's result on success
        """

        try:
            return self.deletefile(filepath, share)
        except Exception:
            return None

    def createdirectory(self, directory_path, share=DEFAULT_SHARE):
        """
        Puts a file remotely.
        :param directory_path: the path of the directory
        :param share: the share (optional).
        :return:
        """

        # Normalize filepath
        directory_path = ntpath.normpath(directory_path)  # also replaces / with \
        assumed_share, directory_path = ntpath.splitdrive(directory_path)
        if assumed_share != '':
            share = assumed_share[:-1] + "$"

        with self.get_smb_connection() as smb_connection:
            sharing_violation_times = 0
            while True:
                try:
                    smb_connection.createDirectory(share, directory_path)
                    return True
                except Exception as e:
                    if str(e).find('STATUS_SHARING_VIOLATION') >= 0:
                        sharing_violation_times = sharing_violation_times + 1
                        if sharing_violation_times > MAX_SHARING_VIOLATION_TIMES:
                            raise
                        # Not finished, let's wait
                        time.sleep(1)
                    else:
                        raise

    def _exec_generic(self, binary_path,
                      binary_params,
                      optional_output_name=None,
                      optional_working_directory=None):
        """
        Executes a binary and returns its output.
        :param str binary_path: the path of the binary to run
        :param str binary_params: the parameters to pass to the binary, as a cmd string.
        :param str optional_output_name: an optional string representing the output file.
        :param str optional_working_directory: the working directory of the new process.
                                               default is the default share directory.
        :return str: the output.
        """

        win32_process, _ = self.get_iWbemServices().GetObject("Win32_Process")
        if optional_output_name is not None:
            output_filename = optional_output_name
        else:
            output_filename = "{0}\\axonius_output_{1}_{2}.txt".format(FILES_DIRECTORY,
                                                                       get_global_counter(),
                                                                       str(time.time()), )

        command_to_run = r"{0} {1} 1> \\127.0.0.1\{2}\{3} 2>&1".format(
            binary_path, binary_params, DEFAULT_SHARE, output_filename)

        try:
            # MSDN states that win32_proces.create should get NULL in its second paramter to allow the process
            # to be created in the directory the parent process currently has.
            # but 1. this could be the wrong directory (we want to reside in the share directory)
            # and 2. due to a bug in impacket we can not have None, NULL, or anything else here (impacket wmi.py
            # will always try to encode this as string in the dcerpc protocol)
            cwd = optional_working_directory or WmiSmbRunner.default_working_directory
            assert cwd is not None, "working directory for new process is None"
            rv = win32_process.Create(command_to_run, cwd, None)

            # Lets get it's pid.
            pid = int(rv.getProperties()['ProcessId']['value'])
            if pid == 0:
                raise ValueError("cmd with {0} could not be created, pid is 0".format(binary_path))

            # Now we have to wait until the process ends. If it takes too much time terminate it.
            create_time = time.time()
            is_process_terminated = False
            num_of_execquery_exceptions = 0
            while (time.time() - create_time) < MAX_TIMEOUT_FOR_CREATED_SHELL_PROCESS:
                try:
                    query_results = self.execquery(
                        "select ProcessId from Win32_Process where ProcessId={0}".format(pid))
                    if len(query_results) == 0:
                        # No process ID found, the process is terminated
                        is_process_terminated = True
                        # Note that this is the legitimate thing! The process should be terminated because
                        # It has finished! We break the while loop because we have finished waiting for it.
                        break

                    time.sleep(1)
                except Exception:
                    # execquery can fail occasionally when it runs too much. if it happens too much
                    # raise an exception here.
                    num_of_execquery_exceptions = num_of_execquery_exceptions + 1
                    if num_of_execquery_exceptions > 3:
                        raise

            if is_process_terminated is False:
                # We have to terminate it by ourselves. and raise an error
                try:
                    query_results = self.get_iWbemServices().ExecQuery(
                        'select * from Win32_Process where ProcessId={0}'.format(pid))
                    query_results.Next(0xffffffff, 1)[0].Terminate(0)

                    # If its not terminated pop up an error.
                    query_results = self.execquery(
                        "select ProcessId from Win32_Process where ProcessId={0}".format(pid))
                    if len(query_results) != 0:
                        raise ValueError("Process was not terminated")

                except Exception as e:
                    raise ValueError("Pid {0} with process {1} (params {2}...) took too much time and "
                                     "could not be terminated. exception {3}".format(pid,
                                                                                     binary_path,
                                                                                     binary_params[:20],
                                                                                     str(e)))

                raise ValueError("Pid {0} with process {1} (params {2}...) took too much time and had "
                                 "to be terminated".format(pid, binary_path, binary_params[:20]))

            return self.getfile(output_filename)
        finally:
            self._trydeletefile(output_filename)

    def execshell(self, shell_command, optional_output_name=None, optional_working_directory=None):
        """
        Executes a shell command and returns its output.
        :param str shell_command: the command, as you would type it in cmd.
        :param optional_output_name: a param for exec_generic
        :param optional_working_directory: a param for exec_generic
        :return str: the output.
        """

        return self._exec_generic("cmd.exe", "/Q /c {0}".format(shell_command),
                                  optional_output_name=optional_output_name,
                                  optional_working_directory=optional_working_directory)

    def execbinary(self, binary_file_path, binary_params):
        """
        Executes a binary file and returns its output.
        :param binary_file: the binary file.
        :param binary_params: a string of all params to pass to the binary (shell-like -> my_file.exe param1 "param 2"
        :return:
        """

        # What we do:
        # 1. self.putfile
        # 2. same thing like exec shell but without the output redirecting
        # 3. self._trydeletefile

        try:
            with open(binary_file_path, "rb") as f:
                binary_file = f.read()
            binary_path = "{0}\\axonius_binary_{1}_{2}.exe".format(FILES_DIRECTORY,
                                                                   get_global_counter(),
                                                                   str(time.time()))
            self.putfile(binary_path, binary_file)
            return self._exec_generic("cmd.exe", "/Q /c {0} {1}".format(binary_path, binary_params))
        finally:
            self._trydeletefile(binary_path)

    def execmethod(self, object_name, method_name, *args):
        """
        Executes a wmi method with the given args and returns the result.
        e.g. rv = o.execmethod("Win32_Process", "Create", "notepad.exe", "c:\\", None)
        print(rv['ProcessId']['value'])

        :param object_name: the wmi object.
        :param method_name: the method.
        :param args: a list of args to give the method.
        :return: an object that represents the answer.
        """

        object, _ = self.get_iWbemServices().GetObject(object_name)
        method = getattr(object, method_name)
        handle = method(*args)
        result = handle.getProperties()

        # If its not a list, return it as a list, to be in the same standard as execquery.
        if not isinstance(result, list):
            return minimize([result])
        else:
            return minimize(result)

    def execquery(self, query, namespace=None):
        """
        Executes a query.
        :param query: a wql string representing the query.
        :return: a list of objects representing the results of the query.
        """
        if namespace is None:
            namespace = self.__namespace

        line = query.strip('\n')
        if line[-1:] == ';':
            line = line[:-1]
        iEnumWbemClassObject = self.get_iWbemServices(namespace).ExecQuery(line)

        records = []
        while True:
            try:
                pEnum = iEnumWbemClassObject.Next(0xffffffff, 1)[0]
                records.append(pEnum.getProperties())
            except Exception as e:
                if str(e).find('S_FALSE') < 0:
                    raise
                else:
                    break

        iEnumWbemClassObject.RemRelease()
        return minimize(records)

    def execaxr(self, arguments):
        """
        Sends axr.exe and axr.exe.config and runs it with the arguments
        :param arguments: a json object of the arguments
        :return: a json response
        """

        assert os.path.exists(AXR_BINARY_LOCATION), "{0} doesn't exist!".format(AXR_BINARY_LOCATION)
        assert os.path.exists(AXR_CONFIG_BINARY_LOCATION), "{0} doesn't exist!".format(AXR_CONFIG_BINARY_LOCATION)

        with open(AXR_BINARY_LOCATION, "rb") as f:
            exe_binary_file = f.read()
            exe_binary_path = "{0}\\axonius_axr_{1}_{2}.exe".format(FILES_DIRECTORY,
                                                                    get_global_counter(),
                                                                    str(time.time()), )

        with open(AXR_CONFIG_BINARY_LOCATION, "rb") as f:
            config_binary_file = f.read()
            config_binary_path = "{0}.config".format(exe_binary_path)

        try:
            # Transfer both files
            self.putfile(config_binary_path, config_binary_file)
            self.putfile(exe_binary_path, exe_binary_file)

            # Escaping some json.dumps outputs is extremely hard, so we move this with base64.
            output = self.execshell(r"{0} {1}".format(exe_binary_path, base64.b64encode(json.dumps(arguments))))
            try:
                return json.loads(output)
            except Exception:
                # The program must have had an error
                raise ValueError, "AXR Returned an invalid json: {0}".format(output)
        finally:
            self._trydeletefile(config_binary_path)
            self._trydeletefile(exe_binary_path)

    def execpm(self, exe_filepath, wsusscn2_file_path):
        """
        A special function to deal with patch management. Since this flow is extremely
        sensitive (involves sending a couple of files, some of them large) we prefer doing it
        in a sepereate function until we have a generic flow to handle it.

        :param exe_filepath: the filepath of the exe
        :param wsusscn2_file_path: the filepath of the wsusscn2.cab file
        :return:
        """

        with open(exe_filepath, "rb") as f:
            exe_binary_file = f.read()
            exe_binary_path = "{0}\\axonius_pm_{1}_{2}.exe".format(FILES_DIRECTORY,
                                                                   get_global_counter(),
                                                                   str(time.time()), )

        with open(wsusscn2_file_path, "rb") as f:
            wsusscn2_binary_file = f.read()
            wsusscn2_binary_path = "{0}\\axonius_wsusscn2.cab".format(FILES_DIRECTORY)

        try:
            # Transfer both files
            self.putfile(wsusscn2_binary_path, wsusscn2_binary_file)
            self.putfile(exe_binary_path, exe_binary_file)

            return self.execshell(r"{0} {1}".format(exe_binary_path, wsusscn2_binary_path))
        finally:
            self._trydeletefile(wsusscn2_binary_path)
            self._trydeletefile(exe_binary_path)

    def exec_pm_online(self, pm_type):
        """
        A special function to deal with patch management on an online environment (computers which are internet
        accessible). This is a sensitive function since it is opening RPC interfaces.
        :param pm_type: rpc (remote) or smb (via file transfer)
        :return:
        """
        def pm_rpc():
            """
            Executes pm status through rpc.
            :return:
            """
            return self.remotewua.search_online("IsInstalled=0")

        def pm_smb():
            """
            Executes pm status through smb.
            """
            rv = self.execbinary(AXPM_BINARY_LOCATION, "1")
            try:
                return json.loads(rv)
            except Exception:
                # The program must have had an error
                raise ValueError, "AXPM Returned an invalid json: {0}".format(rv)

        if pm_type == "rpc":
            return pm_rpc()
        elif pm_type == "smb":
            return pm_smb()
        elif pm_type == "rpc_and_fallback_smb":
            # Execute first rpc, if that fails, execute through smb.
            try:
                return pm_rpc()
            except Exception:
                return pm_smb()
        else:
            raise ValueError, "exec_pm_online: unsupported method!"

    # TODO: This will attempt even on legitimate errors like access denied. fix that
    @retry(stop_max_attempt_number=MAX_NUM_OF_TRIES_PER_CONNECT, wait_fixed=TIME_TO_REST_BETWEEN_CONNECT_RETRY)
    def connect(self):
        """
        Just tries to connect to the host.
        :return: True on successful connection, or exception otherwise.
        """

        # The actual DCOM interface
        self.dcom = DCOMConnection(self.address, self.username, self.password, self.domain, self.lmhash, self.nthash,
                                   self.aes_key, oxidResolver=True, doKerberos=self.use_kerberos, kdcHost=self.dc_ip)

    @retry(stop_max_attempt_number=MAX_NUM_OF_GET_DEFAULT_WORKING_DIRECTORY)
    def __get_default_working_directory(self):
        result = self.execquery("select Name, Path from win32_share where Name='{0}'".format(DEFAULT_SHARE))
        return result[0]['Path']

    def __initialize_smb_connection(self):
        """
        Initialize the usage after we connect. for example, we create the working directory and get its actual location
        in this function
        :return: None
        """
        # If we did not create the directory yet, create it. This is a thing we must do only once.
        if WmiSmbRunner.did_create_files_directory is False:
            try:
                self.createdirectory(FILES_DIRECTORY)
                WmiSmbRunner.did_create_files_directory = True
            except SessionError as e:
                # This is a legitimate error - it means the directory already exists
                if "STATUS_OBJECT_NAME_COLLISION" not in str(e):
                    raise

        # We must get the directory in which the default share resides, since this is a parameter we pass
        # to win32_process.create, to create processes with the right current working directory.
        # Note! setting this to c:\\ could not only fail the shell processes, but also result in a failure
        # of deleting filse from the customer!
        if WmiSmbRunner.default_working_directory is None:
            try:
                WmiSmbRunner.default_working_directory = self.__get_default_working_directory()
            except Exception as e:
                raise ValueError(
                    "Unexpected error occured: coludn't find the physical path of {0}: {1}".format(
                        DEFAULT_SHARE, str(e)))

    def before_close(self):
        """
        Some things we have to do before we close the smb connection.
        :return:
        """
        # This is relevant only to connections that used smb. this function is called when the whole class finishes
        # so there is just one thread which will run it.
        if self.__is_smb_connection_initialized is False:
            return

        # sometimes, files are not being deleted and are left on the machine.
        # we need to delete all files that start with axonius_* for that, both on the default working directory
        # and in the files directory. we delete from the default working directory since this is where we have been
        # putting files before we put them in a specific directory, so we want to delete old files that currently reside
        # in our customers.
        # do note that this command delete all axonius files that are older than 1 day.
        # The reason we delete files that are older than 1 day is that this command gets only "days" and deleting
        # all axonius files right now is a bad thing for us since we might be using some of them. as an example
        # if two tests are running and one deletes the other one's files then the other test will fail.

        # [CAUTION!!!]
        # Do not change this command without a CR of several rnd members. we run this command
        # with high privilleges, so we could theoretically delete important files and shut down the organization.
        # [/CAUTION!!!]

        # This will delete all files that start with "axonius_" and are older than 1 day, in the default cwd
        # and in our specific files directory.

        try:
            DO_NOT_EVER_CHANGE_ME_1 = 'forfiles /m axonius_* /D -1 /C "cmd /c del /Q /F @path"'
            DO_NOT_EVER_CHANGE_ME_2 = 'forfiles /p {0} /m axonius_* /D -1 /C "cmd /c del /Q /F @path"'.format(
                FILES_DIRECTORY)

            self.execshell(DO_NOT_EVER_CHANGE_ME_1)
            self.execshell(DO_NOT_EVER_CHANGE_ME_2)
        except Exception:
            # best try
            pass

    def get_iWbemServices(self, namespace="//./root/cimv2"):
        """
        Creates an RPC WMI Object
        :return: an interface for querying wmi
        """
        with self.__rpc_creation_lock:
            if namespace not in self.__iWbemServices_dict:
                iInterface = self.dcom.CoCreateInstanceEx(wmi.CLSID_WbemLevel1Login, wmi.IID_IWbemLevel1Login)
                iWbemLevel1Login = wmi.IWbemLevel1Login(iInterface)
                iWbemServices = iWbemLevel1Login.NTLMLogin(namespace, NULL, NULL)
                if self.rpc_auth_level == 'privacy':
                    iWbemServices.get_dce_rpc().set_auth_level(RPC_C_AUTHN_LEVEL_PKT_PRIVACY)
                elif self.rpc_auth_level == 'integrity':
                    iWbemServices.get_dce_rpc().set_auth_level(RPC_C_AUTHN_LEVEL_PKT_INTEGRITY)

                iWbemLevel1Login.RemRelease()

                self.__iWbemServices_dict[namespace] = iWbemServices

        return self.__iWbemServices_dict.get(namespace)

    @property
    def remotewua(self):
        """
        Creates an RPC WUA Object
        :return: an internal for querying patch management queries
        """

        with self.__rpc_creation_lock:
            if self.__remotewua is None:
                self.__remotewua = RemoteWUAHandler(self.dcom)

        return self.__remotewua

    @contextmanager
    def get_smb_connection(self):
        with self.__smb_connection_creation_lock:
            if self.__is_smb_connection_initialized is False:
                # initialize_smb_connection uses get_smb_connection itself. since we use RLock
                # this won't be a deadlock as we will simply bypass this block (we specificy initialization finished)
                # on the other hand all other threads will wait until the init finishes.
                try:
                    self.__is_smb_connection_initialized = True  # Putting this below will result in a deadlock.
                    self.__initialize_smb_connection()
                except Exception:
                    # Return to False, other threads will try to re-initialize this.
                    self.__is_smb_connection_initialized = False
                    raise

        # Open an SMB connection. We do this again and again to allow parallelism
        smb_connection = SMBConnection(self.address, self.address)
        smb_connection.login(self.username, self.password, self.domain, self.lmhash, self.nthash)
        # set timeout. If we intend to bring large files change that in the future.
        smb_connection.setTimeout(SMB_CONNECTION_TIMEOUT)

        yield smb_connection

        try:
            smb_connection.logout()
        except Exception:
            pass

    def close(self):
        """
        Closes the connection.
        :return: None
        """

        try:
            for ns in self.__iWnemServices_dict.values():
                ns.RemRelease()
        except Exception:
            pass

        try:
            if self.dcom is not None:
                self.dcom.disconnect()
        except Exception:
            pass


def convert_unicode(result):
    # the object returned by w.query is an object that contains some strings. some of them are regular,
    # and some of them are utf-16. if we try to json.dumps a utf-16 string without mentioning encoding="utf-16",
    # an exception will be thrown. on the other side if we mention encoding="utf-16" and have an str("abc")
    # an exception will be thrown as well, because str("abc") is not a utf-16 encoded string, unicode("abc") is.
    # to cut the long story short - we have multiple encodings in our object, we gotta transform everything possible
    # to unicode(s) or s.decode("utf-16")
    def convert(input):
        if isinstance(input, dict):
            return {convert(key): convert(value) for key, value in input.iteritems()}
        elif isinstance(input, list):
            return [convert(element) for element in input]
        elif isinstance(input, str):
            try:
                return unicode(input)
            except UnicodeDecodeError:
                # Its probably utf-16
                return input.decode("utf-16", errors="ignore")
        else:
            return input

    return convert(result)


def minimize(result):
    """
    We have a lot of "garbage" returned by impacket. we only need the "name", "value" combination,
    so lets reduce so very large amount of data.
    :param result: a list of sql result lines. each line is a dict that looks like {"key": {"value": "data", "a": "b"}}
    :return: the same set of lines but {"key": "data"} and all other non-relevant keys removed.
    """

    # For each for each line in the result -> for each column in a line -> get the value.
    minified_result = []
    for line in result:
        new_line = {}
        for column_name, column_value in line.items():
            new_line[column_name] = column_value.get("value")

        minified_result.append(new_line)

    return minified_result


def run_command(w, command_type, command_args):
    try:
        if command_type == "query":
            result = w.execquery(*command_args)

        elif command_type == "method":
            result = w.execmethod(*command_args)

        elif command_type == "shell":
            result = w.execshell(*command_args)

        elif command_type == "getfile":
            result = w.getfile(*command_args)

        elif command_type == "putfile":
            result = w.putfile(*command_args)

        elif command_type == "deletefile":
            result = w.deletefile(*command_args)

        elif command_type == "execbinary":
            result = w.execbinary(*command_args)

        elif command_type == "pm":
            result = w.execpm(*command_args)

        elif command_type == "pmonline":
            result = w.exec_pm_online(*command_args)

        elif command_type == "axr":
            result = w.execaxr(*command_args)

        else:
            raise ValueError("command type {0} does not exist".format(command_type))

        result = {"status": "ok", "data": result}
    except Exception:
        # Note that we put here value because soon we are going to get it in minimize_and_convert
        # print "\n" + get_exception_string() + "\n" # Useful for debugging.
        result = {"status": "exception", "data": get_exception_string()}

    return result


def number_of_different_rpc_objects(commands):
    """
    Returns the number of different RPC objects we need to create for this set of commands.
    :param list commands: a list of commands that we get as params to the program
    :return:
    """
    usages = {"wmi": 0, "wua": 0}

    for command in commands:
        command_type = command['type']

        if command_type in ["query", "method", "shell", "execbinary"]:
            usages["wmi"] = 1

        elif command_type in ["pm", "pmonline"]:
            usages["wua"] = 1

    return sum(usages.values())


if __name__ == '__main__':
    _, domain, username, password, address, namespace, commands = sys.argv
    tp = ThreadPool(processes=40)
    try:
        # Commands is a json formatted list of commands.
        commands = json.loads(commands)

        # We currently do not support in creating more than 1 rpc object. This is due to impacket
        # not implementing it, and also not being able to run thread safely.
        # the only soltuion as i see it right now is to run commands not in parallel, and this is super slow.
        # that is why if we want to run different types of rpc's we should run this binary a couple of times.
        assert number_of_different_rpc_objects(commands) < 2

        final_result_array = [None for i in range(len(commands))]
        queries_left = [True for i in range(len(commands))]

        # We are going to try to get each one of these queries a couple of times.
        # Between each try, we'll query only what we haven't queried yet, and we'll reconnect.
        consecutive_failures = 0
        while consecutive_failures < MAX_NUM_OF_CONSECUTIVE_QUERY_FAILURES:
            consecutive_failures += 1
            # If we have something left, lets connect and run it.
            if any(queries_left):
                timer_start = time.time()
                with WmiSmbRunner(address, username, password, domain=domain, namespace=namespace) as w:
                    # First, add every one needed.
                    for i, is_left in enumerate(queries_left):
                        if is_left is True:
                            #  We need to run command[i]
                            command_type, command_args = (commands[i]['type'], commands[i]['args'])
                            final_result_array[i] = tp.apply_async(run_command, (w, command_type, command_args))

                    # Now wait for all of the added ones to finish to finish
                    # queries_left are the queries that did not succeed with "ok",
                    # but queries_left_for_round are the queries that returned any answer ("ok", "exception", etc)
                    # so we don't need to do anything with them this round
                    queries_left_for_round = list(queries_left)  # use list to make a copy() and not use the same ref
                    while any(queries_left_for_round) and (time.time() - timer_start) < TIMER_RESET_FOR_EACH_REQUEST_IN_SECONDS:
                        for i, is_left in enumerate(queries_left):
                            if is_left is True:
                                # any query left can be one that hasn't finished and one that has failed
                                # before due to an exception
                                if type(final_result_array[i]) is not dict and final_result_array[i].ready() is True:
                                    final_result_array[i] = final_result_array[i].get()
                                    queries_left_for_round[i] = False

                                    # Check if we are done with it.
                                    if final_result_array[i]["status"] == "ok":
                                        queries_left[i] = False
                                        queries_left_for_round[i] = False
                                        timer_start = time.time()
                                        consecutive_failures = 0
                        time.sleep(TIME_TO_SLEEP_BETWEEN_EACH_ANSWER_CHECK_IN_SECONDS)

                    # At this point some queries succeeded, some queries failed due to an exception (eg network problem)
                    # and some queries failed due to timeout. Those which have failed due to a timeout should have
                    # a timeout error, they are the only one that doesn't contain dicts.
                    for i, is_left in enumerate(queries_left):
                        if is_left is True and type(final_result_array[i]) is not dict:
                            final_result_array[i] = {"status": "exception", "data": "Timeout on request"}
            else:
                break

        # To see it normally, change to(json.dumps("", indent=4)
        print json.dumps(convert_unicode(final_result_array), encoding="utf-16")
        sys.stdout.flush()

    except Exception:
        # At this point we can have many threads which are not daemon threads. we need to forcefully exit.
        sys.stderr.write(get_exception_string())
        os._exit(-1)

    finally:
        tp.terminate()

    sys.exit(0)
