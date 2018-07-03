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

from impacket.dcerpc.v5.dtypes import NULL
from impacket.dcerpc.v5.dcom import wmi
from impacket.dcerpc.v5.dcomrt import DCOMConnection
from impacket.dcerpc.v5.rpcrt import RPC_C_AUTHN_LEVEL_PKT_PRIVACY, RPC_C_AUTHN_LEVEL_PKT_INTEGRITY, \
    RPC_C_AUTHN_LEVEL_NONE
from impacket.smbconnection import SMBConnection
from multiprocessing.pool import ThreadPool
from retrying import retry
from contextlib import contextmanager
from handlers.remotewua import RemoteWUAHandler


MAX_NUM_OF_CONSECUTIVE_QUERY_FAILURES = 3    # Maximum number of times we can fail with not even one success
MAX_NUM_OF_TRIES_PER_CONNECT = 3    # Maximum number of tries to connect.
TIME_TO_REST_BETWEEN_CONNECT_RETRY = 3 * 1000   # 3 seconds.
SMB_CONNECTION_TIMEOUT = 60 * 30  # 30 min timeout. Change that for even larger files
MAX_SHARING_VIOLATION_TIMES = 5  # Maximum legitimate error we can have in smb connection
MAX_TIMEOUT_FOR_CREATED_SHELL_PROCESS = 60 * 2  # The amount of seconds we wait for the created shell process to finish

# each request gets this amount of seconds to return. If one returns, the timer of all the rest resets.
TIMER_RESET_FOR_EACH_REQUEST_IN_SECONDS = 180
TIME_TO_SLEEP_BETWEEN_EACH_ANSWER_CHECK_IN_SECONDS = 2
DEFAULT_SHARE = "ADMIN$"    # A writeable share from which we will be grabbing shell output. TODO: Check IPC$

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

    def __init__(self, address, username, password, domain='', dc_ip=None, lmhash='', nthash='', aes_key=None,
                 use_kerberos=False, rpc_auth_level="default", namespace="//./root/cimv2"):
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
        self.namespace = namespace
        self.dcom = None
        self.rpc_creation_lock = threading.Lock()
        self.__iWbemServices = None
        self.__remotewua = None

        if aes_key is not None:
            self.use_kerberos = True

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __del__(self):
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

    def _exec_generic(self, binary_path, binary_params):
        """
        Executes a binary and returns its output.
        :param str binary_path: the path of the binary to run
        :param str binary_params: the parameters to pass to the binary, as a cmd string.
        :return str: the output.
        """

        win32_process, _ = self.iWbemServices.GetObject("Win32_Process")
        output_filename = "axonius_output_{0}_{1}.txt".format(get_global_counter(), str(time.time()), )
        command_to_run = r"{0} {1} 1> \\127.0.0.1\{2}\{3} 2>&1".format(
            binary_path, binary_params, DEFAULT_SHARE, output_filename)
        is_process_created = False

        try:
            # Open the process. We specify c:\\ just because we have to specify something valid.
            # TODO: Change c:\\ to something else. "None" does not work (as it should, by msdn documentation)
            # TODO: and env variables are not supported. so we assume c:\\ is there.
            rv = win32_process.Create(command_to_run, "c:\\", None)

            # Lets get it's pid.
            pid = int(rv.getProperties()['ProcessId']['value'])
            if pid == 0:
                raise ValueError("cmd with {0} could not be created, pid is 0".format(binary_path))

            is_process_created = True

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
                    query_results = self.iWbemServices.ExecQuery(
                        'SELECT * from Win32_Process where Handle ={0}'.format(pid))
                    query_results.Next(0xffffffff, 1)[0].Terminate(0)

                    # If its not terminated pop up an error.
                    query_results = self.execquery(
                        "select ProcessId from Win32_Process where ProcessId={0}".format(pid))
                    if len(query_results) != 0:
                        raise ValueError("Process was not terminated")
                except Exception as e:
                    raise ValueError("Process {0} with cmd {1} (params {2}...} took too much time and "
                                     "could not be terminated. exception {3}".format(pid, binary_path,
                                                                                     binary_params[:20], repr(e)))

                raise ValueError("Process {0} with cmd {1} (params {2}...) took too much time and had "
                                 "to be terminated".format(pid, binary_path, binary_params[:20]))

            return self.getfile(output_filename)
        finally:
            if is_process_created is True:
                # If this raises exceptions, its probably because it can't delete the file, because we couldn't
                # terminate the process...
                self.deletefile(output_filename)

    def execshell(self, shell_command):
        """
        Executes a shell command and returns its output.
        :param str shell_command: the command, as you would type it in cmd.
        :return str: the output.
        """

        return self._exec_generic("cmd.exe", "/Q /c {0}".format(shell_command))

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
        # 3. self.deletefile

        did_put_file = False
        try:
            with open(binary_file_path, "rb") as f:
                binary_file = f.read()
            binary_path = "axonius_binary_{0}_{1}.exe".format(get_global_counter(), str(time.time()), )
            did_put_file = self.putfile(binary_path, binary_file)
            return self._exec_generic("cmd.exe", "/Q /c {0} {1}".format(binary_path, binary_params))
        finally:
            if did_put_file is True:
                self.deletefile(binary_path)

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

        object, _ = self.iWbemServices.GetObject(object_name)
        method = getattr(object, method_name)
        handle = method(*args)
        result = handle.getProperties()

        # If its not a list, return it as a list, to be in the same standard as execquery.
        if not isinstance(result, list):
            return minimize([result])
        else:
            return minimize(result)

    def execquery(self, query):
        """
        Executes a query.
        :param query: a wql string representing the query.
        :return: a list of objects representing the results of the query.
        """

        line = query.strip('\n')
        if line[-1:] == ';':
            line = line[:-1]
        iEnumWbemClassObject = self.iWbemServices.ExecQuery(line)

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
            exe_binary_path = "axonius_pm_{0}_{1}.exe".format(get_global_counter(), str(time.time()), )

        with open(wsusscn2_file_path, "rb") as f:
            wsusscn2_binary_file = f.read()
            wsusscn2_binary_path = "axonius_wsusscn2.cab".format(get_global_counter(), str(time.time()), )

        did_put_exe_file = False
        did_put_wsusscn2_file = False
        try:
            # We have to get the path of our default share, or else the exe will fail, since we can't
            # open such files from a share. we have to use the physical path.
            # If path isn't there, we need to raise an exception. It must be in the result.
            shell_details = self.execshell("net share {0}".format(DEFAULT_SHARE)).splitlines()
            try:
                physical_path = [line[4:].strip() for line in shell_details if line.lower().startswith("path")][0]
            except Exception:
                raise ValueError(
                    "Unexpected error occured: coludn't find the physical path of {0}".format(DEFAULT_SHARE))

            # Transfer both files
            did_put_wsusscn2_file = self.putfile(wsusscn2_binary_path, wsusscn2_binary_file)
            did_put_exe_file = self.putfile(exe_binary_path, exe_binary_file)

            return self.execshell(r"{0} {1}\{2}".format(exe_binary_path, physical_path, wsusscn2_binary_path))
        finally:
            if did_put_wsusscn2_file is True:
                self.deletefile(wsusscn2_binary_path)

            if did_put_exe_file is True:
                self.deletefile(exe_binary_path)

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

    @property
    def iWbemServices(self):
        """
        Creates an RPC WMI Object
        :return: an interface for querying wmi
        """
        with self.rpc_creation_lock:
            if self.__iWbemServices is None:
                iInterface = self.dcom.CoCreateInstanceEx(wmi.CLSID_WbemLevel1Login, wmi.IID_IWbemLevel1Login)
                iWbemLevel1Login = wmi.IWbemLevel1Login(iInterface)
                iWbemServices = iWbemLevel1Login.NTLMLogin(self.namespace, NULL, NULL)
                if self.rpc_auth_level == 'privacy':
                    iWbemServices.get_dce_rpc().set_auth_level(RPC_C_AUTHN_LEVEL_PKT_PRIVACY)
                elif self.rpc_auth_level == 'integrity':
                    iWbemServices.get_dce_rpc().set_auth_level(RPC_C_AUTHN_LEVEL_PKT_INTEGRITY)

                iWbemLevel1Login.RemRelease()

                self.__iWbemServices = iWbemServices

        return self.__iWbemServices

    @property
    def remotewua(self):
        """
        Creates an RPC WUA Object
        :return: an internal for querying patch management queries
        """

        with self.rpc_creation_lock:
            if self.__remotewua is None:
                self.__remotewua = RemoteWUAHandler(self.dcom)

        return self.__remotewua

    @contextmanager
    def get_smb_connection(self):
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
            if self.iWbemServices is not None:
                self.iWbemServices.RemRelease()
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
