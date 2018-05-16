import logging
logger = logging.getLogger(f"axonius.{__name__}")
from netmiko import ConnectHandler
import re

from axonius.adapter_exceptions import AdapterException
from axonius.utils.parsing import format_mac

from axonius.clients.cisco.abstract import *


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
            lines = lines.split('\n')
            lines = list(filter(lambda x: x.startswith('internet'),
                                map(lambda x: x.lower().expandtabs(tabsize=8).strip(), lines)))
            return SshArpCiscoData(lines)
        except Exception:
            logger.exception("Running shell arp command failed")

    def _query_dhcp_leases(self):
        try:
            lines = self._sess.send_command("show ip dhcp binding")
            return SshDhcpCiscoData(lines)
        except Exception:
            logger.exception("Exception in query dhcp Leases")

    def _query_cdp_table(self):
        try:
            lines = self._sess.send_command("show cdp neighbors detail")
            return SshCdpCiscoData(lines)
        except Exception:
            logger.exception("Exception in query dhcp Leases")


class SshCdpCiscoData(CdpCiscoData):

    @staticmethod
    def _parse_cdp_table(text):
        '''-------------------------
    Device ID: dhcp-slave
    Entry address(es): 
      IP address: 10.0.0.3
    Platform: Cisco 2691,  Capabilities: Switch IGMP 
    Interface: FastEthernet0/1,  Port ID (outgoing port): FastEthernet0/0
    Holdtime : 136 sec

    Version :
    Cisco IOS Software, 2600 Software (C2691-ENTSERVICESK9-M), Version 12.4(13b), RELEASE SOFTWARE (fc3)
    Technical Support: http://www.cisco.com/techsupport
    Copyright (c) 1986-2007 by Cisco Systems, Inc.
    Compiled Tue 24-Apr-07 15:33 by prod_rel_team

    advertisement version: 2
    VTP Management Domain: ''
    Duplex: half
        '''
        text = text.expandtabs(tabsize=8)

        # Split to entries, skip the header
        entries = text.split('-------------------------')[1:]
        logger.info(f'got {len(entries)} entries')
        return entries

    @staticmethod
    def parse_entry_block(block):
        block = block.strip()
        if block.splitlines()[0].strip().endswith(':'):
            assert block.splitlines()[0].count(':') == 1
            return [tuple(map(str.strip, block.split(':', 1)))]
        lines = sum(list(line.split(',  ') for line in block.splitlines()), [])
        return list(map(lambda line: tuple(map(str.strip, line.split(':', 1))), lines))

    @staticmethod
    def translate_entry(entry):
        result = {}
        for key, value in [('IP address', 'ip'), ('Version', 'version'), ('Device ID', 'hostname'),
                           ('Port ID (outgoing port)', 'iface'), ('Platform', 'device_model')]:
            if key in entry:
                logger.debug(f'entry = {entry}')
                result[value] = entry[key]
        return result

    @staticmethod
    def parse_entry(entry):
        entry = entry.strip()
        # TODO: We are converting the data to dict, but it may appear more then once,
        # (For example IP address) . I wasn't able to achive this state so for now
        # we'll throw anything that appear more then once.
        data = dict(sum(map(SshCdpCiscoData.parse_entry_block, entry.split('\n\n')), []))
        return SshCdpCiscoData.translate_entry(data)

    def _parse(self):
        try:
            table = self._parse_cdp_table(self._raw_data)
        except Exception:
            logger.exception('Exception while parsing cdp raw data')
            return

         # Skip the headers line
        for line in table:
            try:
                yield self.parse_entry(line)
            except Exception:
                logger.exception('Exception while paring cdp line')


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
        # name is constant cisco?
        return {'ip': ip, 'mac': format_mac(mac), 'iface': iface, 'ip-expires': expires, 'ip-type': type_}

    def _parse(self):
        try:
            table = self._parse_dhcp_table(self._raw_data)
        except Exception:
            logger.exception('Exception while parsing dhcp raw data')
            return

        # Skip the headers line
        for line in table[1:]:
            try:
                yield self._parse_dhcp_line(line)
            except Exception:
                logger.exception('Exception while paring dchp line')


class SshArpCiscoData(ArpCiscoData):

    def _parse(self):
        for entry in self._raw_data:
            try:
                entry = entry.split()
                mac, ip, iface = format_mac(entry[3]), entry[1], entry[5]
                yield {'mac': mac, 'ip': ip, 'iface': iface}
            except Exception:
                logger.exception('Exception while paring arp line')
