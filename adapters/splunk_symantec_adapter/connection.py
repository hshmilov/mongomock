import time

from splunk_symantec_adapter.plugins import splunk_split_symantec_win, splunk_split_symantec_mac
from splunklib.client import connect, Service
from splunklib.results import ResultsReader


class SplunkConnection(object):
    def __init__(self, host, port, username, password, logger):
        self.conn_details = {'host': host, 'port': port, 'username': username, 'password': password}
        self.conn = None
        self.logger = logger

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

    def __del__(self):
        if hasattr(self, 'conn') and self.is_connected:
            self.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()

    @staticmethod
    def parse_time(t):
        return time.mktime(time.strptime(t, '%Y-%m-%d %H:%M:%S'))

    def fetch(self, search, split_raw, earliest=None):
        if earliest is not None:
            if not isinstance(earliest, str):
                earliest = str(earliest)
        job = self.conn.jobs.oneshot(search, count=0, earliest_time=earliest)
        reader = ResultsReader(job)
        devices_count = 1
        for result in reader:
            devices_count += 1
            if devices_count % 1000 == 0:
                self.logger.info(f"Got {devices_count} devices so far")
            raw = result[b'_raw'].decode('utf-8')
            new_item = split_raw(raw)
            if new_item is not None:
                yield new_item

    def get_symantec_active_hosts(self, past):
        current_hosts = []
        for item in self.fetch('search source=*scm_agent_act*', lambda raw: raw.split(',', 8)[5], f'-{past}h'):
            if item in current_hosts:
                continue
            current_hosts.append(item)
        return current_hosts

    def get_symantec_devices_info(self, last_ts=None):
        current_hosts = []

        mac_hosts = self.fetch('search source=*agt_security* APPLE', splunk_split_symantec_mac, last_ts)
        for host in mac_hosts:
            if host['name'] not in current_hosts:
                current_hosts.append(host['name'])
                yield host
        win_hosts = self.fetch('search source=*agt_system* Operating System', splunk_split_symantec_win, last_ts)
        for host in win_hosts:
            if host['name'] not in current_hosts:
                current_hosts.append(host['name'])
                yield host
