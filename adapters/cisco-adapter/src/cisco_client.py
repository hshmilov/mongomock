import paramiko
from axonius.adapter_exceptions import AdapterException
from axonius.parsing_utils import format_mac

timeout_seconds = 45


class CiscoClient(object):

    def __init__(self, logger, host, username, password, port=22):
        self.logger = logger
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.client = None
        self.connect()

    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.WarningPolicy())
            self.client.connect(hostname=self.host, port=self.port, username=self.username, password=self.password,
                                allow_agent=False, look_for_keys=False, timeout=timeout_seconds)
        except Exception:
            self.logger.exception("Failed connecting to cisco")
            raise AdapterException()

    def get_parsed_arp(self):
        try:
            (stdin, stdout, stderr) = self.client.exec_command("show arp", timeout=timeout_seconds)
            lines = stdout.readlines()

            for line in lines:
                line = line.strip().lower()
                if not line.startswith('internet'):
                    continue
                line = line.split()
                yield {'IP': line[1], 'MAC': format_mac(line[3]), 'Interface': line[5]}
        except Exception:
            self.logger.exception("Running shell arp command failed")
            raise AdapterException()

    def close(self):
        """ Closes the connection """
        self.client.close()
        self.client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
