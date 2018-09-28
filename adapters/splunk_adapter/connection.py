import logging
import time

from axonius.utils.parsing import format_ip, format_mac
from splunklib.client import Service, connect
from splunklib.results import ResultsReader, Message

logger = logging.getLogger(f'axonius.{__name__}')

# The default value of splunk is 50,000 but if we can't get it we go for a lower number.
# This is effectively the paging size.
DEFAULT_MAXIMUM_RESULT_ROWS = 10000


class SplunkConnection(object):
    def __init__(self, host, port, username, password, token=None):
        self.conn_details = {'host': host, 'port': port, 'username': username, 'password': password}
        if token:
            self.conn_details['token'] = token
        self.conn = None
        self.__maximum_result_rows = None

    @property
    def is_connected(self):
        return self.conn is not None

    def connect(self):
        connection = connect(**self.conn_details)
        assert isinstance(connection, Service)
        self.conn = connection

        try:
            self.__maximum_result_rows = int(self.conn.confs["limits"]["restapi"]["maxresultrows"])
            logger.info(f"maxresultrows config (paging max) is {self.__maximum_result_rows}")
        except Exception:
            logger.exception(f"Couldn't get maxresultrows via the api, setting it to {DEFAULT_MAXIMUM_RESULT_ROWS}")
            self.__maximum_result_rows = DEFAULT_MAXIMUM_RESULT_ROWS

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
        # the format is always "ID,Date,Time,Description,IPAddress,HostName,MAC Address"
        # as described in https://www.techrepublic.com/article/solutionbase-using-audit-logs-to-monitor-dhcp-server/
        line_split = raw_line.split(',')
        raw_device = dict()
        raw_device['ip'] = line_split[4]
        raw_device['hostname'] = line_split[5]
        raw_device['mac'] = line_split[6]
        return raw_device

    @staticmethod
    def parse_nexpose(raw_line):
        return dict([x.split('="', 1) for x in raw_line[:-1].split('", ')])

    def fetch(self, search, split_raw, earliest, maximum_records_per_search, device_type):
        try:
            if earliest is not None:
                if not isinstance(earliest, str):
                    earliest = str(earliest)

            job = self.conn.jobs.create(search,
                                        exec_mode="blocking",
                                        earliest_time=earliest,
                                        max_count=maximum_records_per_search)

            result_count = int(job['resultCount'])
            logger.info(f"{device_type}: Got {result_count} events, out of the {maximum_records_per_search} we requested.")

            if result_count > maximum_records_per_search:
                # Prevent a bigger loop than we expected.
                result_count = maximum_records_per_search

            offset = 0
            paging_count = self.__maximum_result_rows
            devices_count = 0

            logger.info(f"Starting to fetch with counts of {paging_count}")

            # Implement paging.
            while offset < result_count:
                try:
                    reader = ResultsReader(job.results(count=paging_count, offset=offset))
                    logger.info(f"Starting to fetch a new page, offset is {offset}")
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
                        except Exception:
                            logger.exception("The data did not return as expected. we got {0}".format(result))
                except Exception:
                    logger.exception(f"Problem reading page at offset {offset}, continuing")

                offset += paging_count

            # finish
            job.cancel()
        except Exception:
            logger.exception(f'Problem fetching with search {search}')

    def get_devices(self, earliest, maximum_records_per_search, fetch_plugins_dict):
        yield from self.fetch('search index=winevents sourcetype=DhcpSrvLog',
                              SplunkConnection.parse_dhcp,
                              earliest,
                              maximum_records_per_search,
                              'DHCP')
        yield from self.fetch('search sourcetype="*Cisco*"  AND "from port"  AND "to port"',
                              SplunkConnection.parse_cisco_port,
                              earliest,
                              maximum_records_per_search,
                              'Cisco client port')
        yield from self.fetch('search sourcetype="*Cisco*" AND "Target MAC Address"',
                              SplunkConnection.parse_cisco_arp,
                              earliest,
                              maximum_records_per_search,
                              'Cisco client')
        yield from self.fetch('search sourcetype="*cisco*" AND NOT "(Target MAC Address) [" AND "mac= "',
                              SplunkConnection.parse_cisco_sig_alarm,
                              earliest,
                              maximum_records_per_search,
                              'Cisco client SIG')
        if fetch_plugins_dict.get("nexpose"):
            yield from self.fetch('search sourcetype="rapid7:nexpose:asset" site_id=* index=rapid7 | dedup asset_id | fields version asset_id ip hostname site_name version mac description installed_software services',
                                  SplunkConnection.parse_nexpose,
                                  earliest,
                                  maximum_records_per_search,
                                  'Nexpose')
