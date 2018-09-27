import logging
import time

from axonius.utils.parsing import format_ip, format_mac
from splunklib.client import Service, connect
from splunklib.results import ResultsReader, Message

logger = logging.getLogger(f'axonius.{__name__}')


class SplunkConnection(object):
    def __init__(self, host, port, username, password, token=None):
        self.conn_details = {'host': host, 'port': port, 'username': username, 'password': password}
        if token:
            self.conn_details['token'] = token
        self.conn = None

    @property
    def is_connected(self):
        return self.conn is not None

    def connect(self):
        connection = connect(**self.conn_details)
        assert isinstance(connection, Service)
        self.conn = connection

    def close(self):
        self.conn.logout()
        self.conn = None

    def try_close(self):
        if hasattr(self, 'conn') and self.is_connected:
            self.close()

    def __del__(self):
        self.try_close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.try_close()

    @staticmethod
    def parse_cisco_sig_alarm(raw_line):
        raw_device = dict()
        if 'mac= ' in raw_line:
            mac_raw = raw_line[raw_line.find('mac= ') + len('mac= '):].split(' ')[0]
            mac_raw = ':'.join([chars if len(chars) == 2 else '0' + chars for chars in mac_raw.split(':')])
            raw_device['mac'] = format_mac(mac_raw)
        if len(raw_line.split(' ')) > 3:
            raw_device['cisco_device'] = raw_line.split(' ')[3]
        return raw_device

    @staticmethod
    def parse_cisco_port(raw_line):
        raw_device = dict()
        if ' Host ' in raw_line:
            raw_device['mac'] = format_mac(raw_line[raw_line.find(' Host ') + len(' Host '):].split(' ')[0])
        if ' to port ' in raw_line:
            raw_device['port'] = raw_line[raw_line.find(' to port ') + len(' to port '):].split(' ')[0]
        if ' vlan ' in raw_line:
            raw_device['vlan'] = raw_line[raw_line.find(' vlan ') + len(' vlan '):].split(' ')[0]
        if len(raw_line.split(' ')) > 3:
            raw_device['cisco_device'] = raw_line.split(' ')[3]
        return raw_device

    @staticmethod
    def parse_cisco_arp(raw_line):
        raw_device = dict()
        if '(Target MAC Address) [' in raw_line:
            raw_device['mac'] = format_mac(raw_line[raw_line.find(
                '(Target MAC Address) [') + len('(Target MAC Address) ['):].split(',')[0])
        if 'TPA(Destination IP Address) ':
            raw_device['ip'] = format_ip(raw_line[raw_line.find(
                'TPA(Destination IP Address) ') + len('TPA(Destination IP Address) '):].split('[')[0])
        if len(raw_line.split(' ')) > 3:
            raw_device['cisco_device'] = raw_line.split(' ')[3]
        return raw_device

    @staticmethod
    def parse_dhcp(raw_line):
        line_split = raw_line.split(',')
        raw_device = dict()
        raw_device['ip'] = line_split[4]
        raw_device['hostname'] = line_split[5]
        raw_device['mac'] = line_split[6]
        return raw_device

    @staticmethod
    def parse_time(t):
        return time.mktime(time.strptime(t, '%Y-%m-%d %H:%M:%S'))

    def fetch(self, search, split_raw, earliest=None, device_type=''):
        try:
            if earliest is not None:
                if not isinstance(earliest, str):
                    earliest = str(earliest)
            job = self.conn.jobs.oneshot(search, count=0, earliest_time=earliest)
            reader = ResultsReader(job)
            devices_count = 1
            for result in reader:
                if isinstance(result, Message):
                    # splunk can have two types of objects. we need the dict ones and not the message ones.
                    continue
                devices_count += 1
                if devices_count % 1000 == 0:
                    logger.info(f"Got {devices_count} devices so far")
                try:
                    raw = result[b'_raw'].decode('utf-8')
                    new_item = split_raw(raw)
                    if new_item is not None:
                        try:
                            new_item['raw_splunk_insertion_time'] = result[b'_time'].decode('utf-8')
                        except Exception:
                            logger.exception(f"Couldn't fetch raw splunk insertion time for {new_item}")
                        yield new_item, device_type
                except Exception as err:
                    logger.exception("The data did not return as expected. we got {0}".format(repr(raw)))
        except Exception:
            logger.exception(f'Problem fetching with search {str(search)}')

    def get_devices(self, earliest=None):
        yield from self.fetch('search index=winevents sourcetype=DhcpSrvLog',
                              SplunkConnection.parse_dhcp, earliest, 'DHCP')
        yield from self.fetch('search sourcetype="*Cisco*"  AND "from port"  AND "to port"',
                              SplunkConnection.parse_cisco_port, earliest, 'Cisco client port')
        yield from self.fetch('search sourcetype="*Cisco*" AND "Target MAC Address"',
                              SplunkConnection.parse_cisco_arp, earliest, 'Cisco client')
        yield from self.fetch('search sourcetype="*cisco*" AND NOT "(Target MAC Address) [" AND "mac= "',
                              SplunkConnection.parse_cisco_sig_alarm, earliest, 'Cisco client SIG')
