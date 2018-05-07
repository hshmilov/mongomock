import logging
logger = logging.getLogger(f"axonius.{__name__}")
from netmiko import ConnectHandler
import re

from axonius.adapter_exceptions import AdapterException
from axonius.utils.parsing import format_mac

from axonius.clients.cisco.abstract import ArpCiscoData, DhcpCiscoData, AbstractCiscoClient


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

    def _query_dhcp_leases(self):
        try:
            lines = self._sess.send_command("show ip dhcp binding")
            yield SshDhcpCiscoData(lines)
        except Exception:
            logger.exception("Exception in query dhcp Leases")


class SshDhcpCiscoData(DhcpCiscoData):

    @staticmethod
    def _parse_dhcp_table(text):
        ''' Data Example:
            CiscoEmuRouter# show ip dhcp binding 
            Bindings from all pools not associated with VRF:
            IP address          Client-ID/              Lease expiration        Type
                                Hardware address/
                                User name
            10.0.0.3            0063.6973.636f.2d31.    Mar 13 2002 01:56 AM    Automatic
                                3133.332e.3333.3737.
                                2e64.6561.642d.4661.
                                302f.30
            10.0.0.2            0063.6973.636f.2d31.    Mar 13 2002 01:57 AM    Automatic
                                3133.332e.3333.3737.
                                2e64.6561.642d.4661.
                                302f.30
        '''

        text = text[text.index('IP address'):]
        text = text.expandtabs(tabsize=8)

        header = re.compile(r'([^\s]*(?:\s[^\s]+)? +\s*)')

        lines = text.split('\n')
        headers = header.findall(lines[0])

        def split_line(l):
            splitted = []
            for h in headers:
                splitted.append(l[:len(h)].strip())
                l = l[len(h):]
            splitted.append(l)
            return splitted

        table_row = None
        table = []
        while lines:
            current_line = lines.pop(0)
            if not current_line or current_line[0] != ' ':
                if table_row is not None:
                    if sum([len(x) for x in table_row]) > 0:
                        table.append(table_row)
                table_row = split_line(current_line)
            else:
                table_row = [cell + new_cell.strip() for cell, new_cell in zip(table_row, split_line(current_line))]
        if table_row is not None:
            if sum([len(x) for x in table_row]) > 0:
                table.append(table_row)
        return table

    @staticmethod
    def _parse_dhcp_line(text):
        ip, info, expires, type_ = text
        info = bytes.fromhex(info.replace('.', '')).decode('utf-8')
        info = info.replace('\x00', '')
        name, mac, iface = info.split('-')
        return {'ip': ip, 'name': name, 'mac': format_mac(mac), 'iface': iface, 'ip-expires': expires, 'ip-type': type_}

    def parse(self):
        try:
            table = self._parse_dhcp_table(self._raw_data)
        except Exception:
            logging.exception('Exception while parsing dhcp raw data')
            return

        # Skip the headers line
        for line in table[1:]:
            try:
                yield self._parse_dhcp_line(line)
            except Exception:
                logging.exception('Exception while paring dchp line')


class SshArpCiscoData(ArpCiscoData):

    def parse(self):
        entry = self._raw_data.split()
        mac, ip, iface = format_mac(entry[3]), entry[1], entry[5]
        yield {'mac': mac, 'ip': ip}
