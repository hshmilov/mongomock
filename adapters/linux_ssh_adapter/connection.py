import logging
import socket

import paramiko

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.linux_ssh.data import CommandExecutor
from axonius.utils.memfiles import temp_memfd
from linux_ssh_adapter.consts import NETWORK_TIMEOUT

logger = logging.getLogger(f'axonius.{__name__}')


class LinuxSshConnection:
    """ client for Linux ssh adapter """

    def __init__(self, hostname, port, username, password=None, key=None, is_sudoer=False):
        if password is None and key is None:
            raise ClientConnectionException('password/key is required')

        self._port = port
        self._hostname = hostname
        self._username = username
        self._password = password
        self._key = key

        self._is_sudoer = is_sudoer

        self._client = None

    def __connect(self, key_filename=None):
        self._client.connect(hostname=self._hostname,
                             port=self._port,
                             username=self._username,
                             password=self._password,
                             key_filename=key_filename,
                             look_for_keys=False,
                             timeout=NETWORK_TIMEOUT)

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

    def _execute_ssh_cmdline(self, cmdline):
        """
            This function get command class and should
            initiate it using the client id and the command response
            (stdout + stderr combined), stripped and decoded as string
        """

        chan = self._client.get_transport().open_session(timeout=NETWORK_TIMEOUT)
        chan.set_combine_stderr(True)
        chan.settimeout(NETWORK_TIMEOUT)
        stdout = chan.makefile()
        chan.exec_command(cmdline)
        output = stdout.read()
        output = output.strip().decode('utf-8')
        return output

    def get_commands(self):
        # Pass password if only if sudoer
        password = self._password if self._is_sudoer else None
        yield from CommandExecutor(self._execute_ssh_cmdline, password).get_commands()

    @staticmethod
    def test_reachability(hostname, port):
        test_client = None
        try:
            sock = socket.socket()
            sock.settimeout(NETWORK_TIMEOUT)
            sock.connect((hostname, port))
            test_client = paramiko.Transport(sock)
            test_client.connect()
        except Exception as e:
            logger.exception('test_reachability exception')
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
