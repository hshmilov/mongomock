import logging
logger = logging.getLogger(f"axonius.{__name__}")
import time

from splunklib.client import connect, Service
from splunklib.results import ResultsReader


class SplunkConnection(object):
    def __init__(self, host, port, username, password, token):
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
                logger.info(f"Got {devices_count} devices so far")
            raw = result[b'_raw'].decode('utf-8')
            try:
                new_item = split_raw(raw)
                if new_item is not None:
                    yield new_item
            except Exception as err:
                logger.exception("The data did not return as expected. we got {0}".format(repr(raw)))
                break

    def get_nexpose_devices(self, earliest=None):
        return self.fetch('search sourcetype="rapid7:nexpose:asset" site_id=* index=rapid7 | dedup asset_id | fields version asset_id ip hostname site_name version mac description installed_software services',
                          lambda raw: dict([x.split('="', 1) for x in raw[:-1].split('", ')]), earliest)
