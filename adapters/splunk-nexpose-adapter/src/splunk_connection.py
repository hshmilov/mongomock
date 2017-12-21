import time

from splunklib.client import connect, Service
from splunklib.results import ResultsReader


class SplunkConnection(object):
    def __init__(self, host, port, username, password):
        self.conn_details = {'host': host, 'port': port, 'username': username, 'password': password}
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
            search += ' earliest=' + earliest
        job = self.conn.jobs.create(search)
        while not job.is_done():
            time.sleep(1)
        res = job.results()
        reader = ResultsReader(res)
        for result in reader:
            raw = result[b'_raw'].decode('utf-8')
            new_item = split_raw(raw)
            if new_item is not None:
                yield new_item

    def get_nexpose_devices(self):
        return self.fetch('search sourcetype="rapid7:nexpose:asset" site_id=* index=rapid7 | dedup asset_id | fields version asset_id ip hostname site_name version mac description installed_software services',
                          lambda raw: dict([x[:-1].split('="', 2) for x in raw.split(', ')]))
