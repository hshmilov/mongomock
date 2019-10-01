import logging
import socket

import paramiko
from scp import SCPClient

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.linux_ssh.data import CommandExecutor, MD5FilesCommand
from axonius.utils.memfiles import temp_memfd
from axonius.clients.linux_ssh.consts import DEFAULT_NETWORK_TIMEOUT

logger = logging.getLogger(f'axonius.{__name__}')


class LinuxSshConnection:
    """ client for Linux ssh adapter """

    def __init__(self,
                 hostname,
                 port,
                 username,
                 password=None,
                 key=None,
                 is_sudoer=False,
                 timeout=DEFAULT_NETWORK_TIMEOUT,
                 passphrase=None,
                 sudo_path=None):

        if password is None and key is None:
            raise ClientConnectionException('password/key is required')

        self._port = port
        self._hostname = hostname
        self._username = username
        self._password = password
        self._key = key
        self._timeout = timeout
        self._passphrase = passphrase

        self._is_sudoer = is_sudoer
        self._sudo_path = sudo_path

        self._client = None

    def __connect(self, key_filename=None):
        # pylint: disable=E1123
        self._client.connect(hostname=self._hostname,
                             port=self._port,
                             username=self._username,
                             password=self._password,
                             key_filename=key_filename,
                             look_for_keys=False,
                             timeout=self._timeout,
                             passphrase=self._passphrase)

    def _connect(self):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # I didn't find any way to pass the file data, so we must use memfd
        if self._key:
            with temp_memfd('private_key', self._key) as key_filename:
                self.__connect(key_filename=key_filename)
        else:
            self.__connect()

    def _close(self):
        if self._client:
            self._client.close()
            self._client = None

    def upload_file(self, source_path, remote_path):
        """
        Upload file to remote server via scp
        :param source_path: source file path
        :param remote_path: remote file path
        :return: true on success, otherwise false.
        :notes: file will be overridden if exists on server.
        """
        try:
            logger.debug(f'Trying to upload {source_path} to {remote_path}')
            with SCPClient(self._client.get_transport()) as scp:
                scp.put(source_path, remote_path)
            return True
        except Exception:
            logger.exception('Upload Error')
            return False

    def _execute_ssh_cmdline(self, cmdline):
        """
            This function get command class and should
            initiate it using the client id and the command response
            (stdout + stderr combined), stripped and decoded as string
        """

        chan = self._client.get_transport().open_session(timeout=self._timeout)
        chan.set_combine_stderr(True)
        chan.settimeout(self._timeout)
        stdout = chan.makefile()
        chan.exec_command(cmdline)
        output = stdout.read()
        output = output.strip().decode('utf-8')
        return output

    def get_commands(self, md5_files_list=None):
        # Pass password if only if sudoer
        password = self._password if self._is_sudoer else None
        sudo_path = self._sudo_path if (self._is_sudoer and self._sudo_path) else None
        command_executor = CommandExecutor(self._execute_ssh_cmdline, password, sudo_path=sudo_path)

        if md5_files_list:
            command_executor.add_dynamic_command(MD5FilesCommand(md5_files_list))
        yield from command_executor.get_commands()

    @staticmethod
    def test_reachability(hostname, port, timeout=DEFAULT_NETWORK_TIMEOUT):
        test_client = None
        try:
            sock = socket.socket()
            sock.settimeout(timeout)
            sock.connect((hostname, port))
            test_client = paramiko.Transport(sock)
            test_client.connect()
        except Exception as e:
            logger.exception(f'test_reachability exception on {hostname}')
            return False
        finally:
            if test_client:
                test_client.close()
        return True

    def __enter__(self):
        self._connect()
        return self

    # pylint: disable=C0103
    def __exit__(self, _type, value, tb):
        self._close()
