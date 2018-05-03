import logging
logger = logging.getLogger(f"axonius.{__name__}")
from netmiko import ConnectHandler

from axonius.adapter_exceptions import AdapterException
from axonius.utils.parsing import format_mac

from axonius.clients.cisco.abstract import AbstractCiscoClient, ArpCiscoData


class CiscoSshClient(AbstractCiscoClient):
    def __init__(self, host, username, password, port=22):
        super().__init__()

        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self._sess = None

    def __enter__(self):
        super().__enter__()
        self._sess = ConnectHandler(device_type='cisco_ios', ip=self.host, username=self.username,
                                    password=self.password)
        return self

    def __exit__(self, *args):
        super().__exit__(*args)
        self._sess.disconnect()

    def _query_arp_table(self):
        try:
            lines = self._sess.send_command("show arp")
            for line in lines.split('\n'):
                try:
                    line = line.strip().lower()
                    if not line.startswith('internet'):
                        continue
                    yield SshArpCiscoData(line)
                except Exception:
                    logger.exception(f"Invalid line {line}")
        except Exception:
            logger.exception("Running shell arp command failed")


class SshArpCiscoData(ArpCiscoData):

    def parse(self):
        entry = self._raw_data.split()
        mac, ip, iface = format_mac(entry[3]), entry[1], entry[5]
        yield {'mac': mac, 'ip': ip}
