import logging
import re
import socket
from datetime import timedelta
from collections import namedtuple

import func_timeout
import paramiko
from netmiko import ConnectHandler

from axonius import adapter_exceptions
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.cisco.abstract import (AbstractCiscoClient, ArpCiscoData,
                                            CdpCiscoData, DhcpCiscoData)
from axonius.thread_stopper import StopThreadException
from axonius.utils.parsing import format_mac

logger = logging.getLogger(f'axonius.{__name__}')


DEFAULT_VALIDATE_TIMEOUT = 10
DEFAULT_TIMEOUT = 60


def raise_timeout(sig, frame):
    raise TimeoutError()


class CiscoConsoleClient(AbstractCiscoClient):
    def __init__(self, **kwargs):
        super().__init__()
        for required_arg in ('host', 'username', 'password', 'port'):
            if required_arg not in kwargs:
                raise ClientConnectionException(f'CONSOLE - missing required parmeter "{required_arg}"')

        self.host = kwargs['host']
        self.username = kwargs['username']
        self.password = kwargs['password']
        self.port = kwargs['port']
        self._sess = None

    @staticmethod
    def get_device_type():
        raise NotImplementedError()

    def _validate_connection(self):
        sess = ConnectHandler(device_type=self.get_device_type(),
                              ip=self.host,
                              username=self.username,
                              password=self.password,
                              port=self.port,
                              session_timeout=DEFAULT_VALIDATE_TIMEOUT,
                              blocking_timeout=DEFAULT_VALIDATE_TIMEOUT,
                              timeout=DEFAULT_VALIDATE_TIMEOUT)
        if sess:
            sess.disconnect()

    def validate_connection(self):
        """
        This calls _connect_client in safe, timeout based way.
        Parameters and return type are the same as _connect_client
        """
        # Netmiko ConnectHandler is handling the timeout field badly
        # (for example it doesn't pass the timeout to timeout_auth param in paramiko)
        # lets say for example that we have a  very slow connection -
        # the validate_connection function should work but it is going to take much more then 10
        # seconds which is our timeout.

        timeout = DEFAULT_VALIDATE_TIMEOUT
        timeout = timedelta(seconds=timeout).total_seconds()

        def call_connect_as_stoppable():
            try:
                return self._validate_connection()
            except BaseException as e:
                # this is called from an external thread so if it raises the exception is lost,
                # this allows forwarding exceptions back to the caller
                return e

        try:
            res = func_timeout.func_timeout(
                timeout=timeout,
                func=call_connect_as_stoppable)
            if isinstance(res, BaseException):
                raise res
            return res
        except func_timeout.exceptions.FunctionTimedOut:
            raise adapter_exceptions.ClientConnectionException(f'Connecting {self.host} has timed out')
        except StopThreadException:
            raise adapter_exceptions.ClientConnectionException(f'Connecting has been stopped')

    def __enter__(self):
        super().__enter__()
        self._sess = ConnectHandler(device_type=self.get_device_type(), ip=self.host, username=self.username,
                                    password=self.password, port=self.port, timeout=DEFAULT_TIMEOUT)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        self._sess.disconnect()

    def _query_arp_table(self):
        try:
            lines = self._sess.send_command_timing('show arp')
            lines = lines.split('\n')
            lines = list(filter(lambda x: x.startswith('internet'),
                                map(lambda x: x.lower().expandtabs(tabsize=8).strip(), lines)))
            return ConsoleArpCiscoData(lines, received_from=self.host)
        except Exception:
            logger.exception('Running shell arp command failed')

    def _query_dhcp_leases(self):
        try:
            lines = self._sess.send_command_timing('show ip dhcp binding')
            return ConsoleDhcpCiscoData(lines, received_from=self.host)
        except Exception:
            logger.exception('Exception in query dhcp Leases')

    def _query_cdp_table(self):
        try:
            lines = self._sess.send_command_timing('show cdp neighbors detail')
            return ConsoleCdpCiscoData(lines, received_from=self.host)
        except Exception:
            logger.exception('Exception in query dhcp Leases')

    @staticmethod
    def _query_basic_info():
        logger.warning('basic info isn\'t implemented yet - skipping')


class CiscoSshClient(CiscoConsoleClient):
    @staticmethod
    def get_device_type():
        return 'cisco_ios'

    @staticmethod
    def test_reachability(host, port):
        test_client = None
        try:
            sock = socket.socket()
            sock.settimeout(DEFAULT_VALIDATE_TIMEOUT)
            sock.connect((host, port))
            test_client = paramiko.Transport(sock)
            test_client.connect()
        except Exception as e:
            logger.exception('test_reachability exception')
            return False
        finally:
            if test_client:
                test_client.close()
        return True


class CiscoTelnetClient(CiscoConsoleClient):
    @staticmethod
    def get_device_type():
        return 'cisco_ios_telnet'

    @staticmethod
    def test_reachability(host, port):
        try:
            sock = socket.create_connection((host, port), DEFAULT_VALIDATE_TIMEOUT)
            sock.close()
        except Exception as e:
            logger.exception('test_reachability exception')
            return False
        return True


class ConsoleCdpCiscoData(CdpCiscoData):
    @staticmethod
    def parse_word(title, entry):
        match = re.findall(r'{}:[^\n]\s?(\S.*?)[,\s\(]'.format(re.escape(title)), entry, re.MULTILINE)
        return match[0] if match else None

    @staticmethod
    def parse_til_comma(title, entry):
        match = re.findall(r'{}:[^\n]\s?(\S.*?)[,\n\(]'.format(re.escape(title)), entry, re.MULTILINE)
        return match[0] if match else None

    @staticmethod
    def parse_version(title, entry):
        match = re.findall(r'{} :\s+(.*?)\n\n'.format(re.escape(title)), entry, re.DOTALL)
        return match[0] if match else None

    @staticmethod
    def _parse_cdp_table(text):
        text = text.expandtabs(tabsize=8)

        # Split to entries, skip the header
        entries = text.split('-------------------------')[1:]
        logger.debug(f'got {len(entries)} entries')
        return entries

    @staticmethod
    def parse_entry(entry):
        entry = entry.strip()
        # XXX: We are converting the data to dict, but it may appear more then once,
        # (For example IP address) . I wasn't able to achive this state so for now
        # we'll throw anything that appear more then once.
        result = {}
        for index, title in enumerate(TITLES):
            parsed = PARSERS[index](title, entry)
            if parsed:
                result[CONVERTERS[index]] = parsed
        return result

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


KEYS = ('ipv4',
        'ipv6',
        'version',
        'hostname',
        'remote_iface',
        'iface',
        'device_model')
Keys = namedtuple('CdpKeys', KEYS)
TITLES = Keys(
    ipv6='IPv6 address',
    ipv4='IP address',
    version='Version',
    hostname='Device ID',
    remote_iface='Interface',
    iface='Port ID (outgoing port)',
    device_model='Platform',
)
PARSERS = Keys(
    ipv6=ConsoleCdpCiscoData.parse_word,
    ipv4=ConsoleCdpCiscoData.parse_word,
    version=ConsoleCdpCiscoData.parse_version,
    hostname=ConsoleCdpCiscoData.parse_word,
    remote_iface=ConsoleCdpCiscoData.parse_word,
    iface=ConsoleCdpCiscoData.parse_word,
    device_model=ConsoleCdpCiscoData.parse_til_comma,
)
CONVERTERS = Keys(*(key.replace('ipv6', 'ip').replace('ipv4', 'ip') for key in KEYS))


# XXX: pylint thinks that iterator table_row is not iterable - AX-1898
# pylint: disable=E1133


class ConsoleDhcpCiscoData(DhcpCiscoData):

    @staticmethod
    def _parse_dhcp_table(text):
        text = text[text.index('IP address'):]
        text = text.expandtabs(tabsize=8)

        header = re.compile(r'([^\s]*(?:\s[^\s]+)? +\s*)')

        lines = text.split('\n')
        headers = header.findall(lines[0])

        def split_line(line):
            splitted = []
            for h in headers:
                splitted.append(line[:len(h)].strip())
                line = line[len(h):]
            splitted.append(line)
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
        return {'ip': ip, 'mac': format_mac(mac), 'remote_iface': iface, 'ip-expires': expires, 'ip-type': type_}

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


class ConsoleArpCiscoData(ArpCiscoData):

    def _parse(self):
        for entry in self._raw_data:
            try:
                entry = entry.split()
                mac, ip = entry[3], entry[1]
                # incomplete means that the cisco sent arp and didn't get reply.
                if mac == 'incomplete':
                    continue
                mac = format_mac(mac)
                iface = entry[5] if len(entry) > 5 else ''
                yield {'mac': mac, 'ip': ip, 'remote_iface': iface}
            except Exception:
                logger.exception('Exception while paring arp line')
