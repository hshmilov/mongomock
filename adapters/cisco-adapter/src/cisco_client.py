import logging
import paramiko
import paramiko.util
from paramiko import ChannelException
import time
import random

from axonius.adapter_exceptions import AdapterException
from axonius.parsing_utils import format_mac


paramiko.util.log_to_file('/home/axonius/logs/paramiko.log', logging.DEBUG)
timeout_seconds = 45


class CiscoClient(object):

    def __init__(self, logger, host, username, password, port=22):
        self.logger = logger
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.client = None

    def connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.WarningPolicy())
        self.client.connect(hostname=self.host, port=self.port, username=self.username, password=self.password,
                            allow_agent=False, look_for_keys=False, timeout=timeout_seconds)

    def get_parsed_arp(self, retry_count=5):
        devices_count = 1
        assert isinstance(retry_count, int) and retry_count > 0
        try:
            stdout = None
            for retry_index in range(retry_count):
                try:
                    (stdin, stdout, stderr) = self.client.exec_command("show arp", timeout=timeout_seconds)
                except ChannelException as e:
                    if (retry_index == retry_count - 1) or (e.code != 4):
                        raise
                    # handling 'Resource shortage'
                    time.sleep(1 + random.randint(1, 5))
            devices_count += 1
            if devices_count % 1000 == 0:
                self.logger.info(f"Got {devices_count} devices so far")
            lines = stdout.readlines()

            for line in lines:
                line = line.strip().lower()
                if not line.startswith('internet'):
                    continue
                line = line.split()
                yield {'ip': line[1], 'mac': format_mac(line[3]), 'Interface': line[5]}
        except Exception:
            self.logger.exception("Running shell arp command failed")
            raise AdapterException()

    def close(self):
        """ Closes the connection """
        if self.client is None:
            return
        self.client.close()
        self.client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
