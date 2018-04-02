import logging
logger = logging.getLogger(f"axonius.{__name__}")
from netmiko import ConnectHandler

from axonius.adapter_exceptions import AdapterException
from axonius.utils.parsing import format_mac


class CiscoClient(object):

    def __init__(self, host, username, password, port=22):

        self.host = host
        self.username = username
        self.password = password
        self.port = port

    def get_parsed_arp(self):
        try:
            lines = self._get_arp_lines()

            for line in lines.split('\n'):
                line = line.strip().lower()
                if not line.startswith('internet'):
                    continue
                line = line.split()
                yield {'ip': line[1], 'mac': format_mac(line[3]), 'Interface': line[5]}
        except Exception:
            logger.exception("Running shell arp command failed")
            raise AdapterException()

    def _get_arp_lines(self):
        net_connect = ConnectHandler(device_type='cisco_ios', ip=self.host, username=self.username,
                                     password=self.password)
        try:
            return net_connect.send_command("show arp")
        finally:
            net_connect.disconnect()
