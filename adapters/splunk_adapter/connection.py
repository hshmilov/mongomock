import logging
import time
import re

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
    def parse_cisco_bt(raw_line):
        raw_device = dict()
        if 'M=' in raw_line and (raw_line.find('M=') + len('M=')) < len(raw_line):
            mac_raw = raw_line[raw_line.find('M=') + len('M='):].split(' ')[0]
            mac_raw = ':'.join([chars if len(chars) == 2 else '0' + chars for chars in mac_raw.split(':')])
            raw_device['mac'] = format_mac(mac_raw)
            if not raw_device['mac']:
                return None
        else:
            return None
        line_split = raw_line.split(' ')
        line_split = [item for item in line_split if item]
        if len(line_split) > 3:
            raw_device['cisco_device'] = line_split[3]
        return raw_device

    @staticmethod
    def parse_cisco_sig_alarm(raw_line):
        raw_device = dict()
        if 'mac= ' in raw_line:
            mac_raw = raw_line[raw_line.find('mac= ') + len('mac= '):].split(' ')[0]
            mac_raw = ':'.join([chars if len(chars) == 2 else '0' + chars for chars in mac_raw.split(':')])
            raw_device['mac'] = format_mac(mac_raw)
        line_split = raw_line.split(' ')
        line_split = [item for item in line_split if item]
        if len(line_split) > 3:
            raw_device['cisco_device'] = line_split[3]
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
        line_split = raw_line.split(' ')
        line_split = [item for item in line_split if item]
        if len(line_split) > 3:
            raw_device['cisco_device'] = line_split[3]
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
        line_split = raw_line.split(' ')
        line_split = [item for item in line_split if item]
        if len(line_split) > 3:
            raw_device['cisco_device'] = line_split[3]
        return raw_device

    @staticmethod
    def parse_vpn(raw_line):
        raw_device = dict()
        line_split = raw_line.split(' ')
        line_split = [item for item in line_split if item]
        if 'PulseSecure:' in line_split:
            raw_device['hostname'] = line_split[line_split.index('PulseSecure:') - 1]
            if 'NCIP' in line_split:
                raw_device['ip'] = line_split[line_split.index('NCIP') + 1]
        elif 'FLOW_REASSEMBLE_SUCCEED' in raw_line:
            raw_device['hostname'] = line_split[3]
            if 'source' in line_split:
                raw_device['vpn_source_ip'] = line_split[line_split.index('source') + 1]
        else:
            return None
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

    def fetch(self, search, split_raw, earliest, maximum_records_per_search, device_type, send_object_to_raw=False):
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
                            if not send_object_to_raw:
                                new_item = split_raw(raw)
                            else:
                                new_item = split_raw(result)
                            if new_item is not None:
                                try:
                                    new_item['raw_splunk_insertion_time'] = result[b'_time'].decode('utf-8')
                                    new_item['raw_line'] = raw
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

    @staticmethod
    def parse_win_events(result):
        raw_object = dict()
        raw_line = result[b'_raw'].decode('utf-8')
        raw_object['hostname'] = result[b'ComputerName'].decode('utf-8')
        raw_object['users'] = []
        users_locations = [user_location.start() + len('Account Name') +
                           1 for user_location in re.finditer('Account Name', raw_line)]
        for user_location in users_locations:
            user_raw = raw_line[user_location:].split('\n')[0].strip()
            raw_object['users'].append(user_raw)
        return raw_object

    @staticmethod
    def parse_landesk(raw_line):
        raw_object = dict()

        if 'DISPLAYNAME' in raw_line:
            raw_object['hostname'] = raw_line[raw_line.find('DISPLAYNAME') + len("DISPLAYNAME") + 2:].split('"')[0]
        if 'host_name' in raw_line:
            raw_object['hostname'] = raw_line[raw_line.find('host_name') + len("host_name") + 2:].split('"')[0]
        if 'IPADDRESS' in raw_line:
            raw_object['ip'] = raw_line[raw_line.find('IPADDRESS') + len("IPADDRESS") + 2:].split('"')[0]
        if 'ip=' in raw_line:
            raw_object['ip'] = raw_line[raw_line.find('ip=') + len("ip=") + 1:].split('"')[0]
        if 'MACADDRESS' in raw_line:
            raw_object['mac'] = raw_line[raw_line.find('MACADDRESS') + len("MACADDRESS") + 2:].split('"')[0]
        if 'mac=' in raw_line:
            raw_object['mac'] = raw_line[raw_line.find('mac=') + len("mac=") + 1:].split('"')[0]
        if 'OSTYPE' in raw_line:
            raw_object['os'] = raw_line[raw_line.find('OSTYPE') + len("OSTYPE") + 2:].split('"')[0]
        if 'os_type' in raw_line:
            raw_object['os'] = raw_line[raw_line.find('os_type') + len("os_type") + 2:].split('"')[0]
        if 'SERIALNUM' in raw_line:
            raw_object['serial'] = raw_line[raw_line.find('SERIALNUM') + len("SERIALNUM") + 2:].split('"')[0]
        if 'LDCHECKINDATE' in raw_line:
            raw_object['last_seen'] = raw_line[raw_line.find('LDCHECKINDATE') + len("LDCHECKINDATE") + 2:].split('"')[0]
        if 'update_time' in raw_line:
            raw_object['last_seen'] = raw_line[raw_line.find('update_time') + len("update_time") + 2:].split('"')[0]
        if 'LOGINNAME' in raw_line:
            raw_object['user'] = raw_line[raw_line.find('LOGINNAME') + len("LOGINNAME") + 2:].split('"')[0]
        if 'user_name' in raw_line:
            raw_object['user'] = raw_line[raw_line.find('user_name') + len("user_name") + 2:].split('"')[0]
        if 'domain=' in raw_line:
            raw_object['domain'] = raw_line[raw_line.find('domain=') + len("domain=") + 1:].split('"')[0]
        return raw_object

    def get_devices(self, earliest, maximum_records_per_search, fetch_plugins_dict):
        yield from self.fetch('search index=lnv_landesk',
                              SplunkConnection.parse_landesk,
                              earliest,
                              maximum_records_per_search,
                              'Landesk')
        fetch_hours = fetch_plugins_dict.get('win_logs_fetch_hours') or 3
        yield from self.fetch('search "SourceName=Microsoft Windows security auditing" AND '
                              '"Audit Success"AND NOT "Account_Name=SYSTEM" |dedup ComputerName',
                              SplunkConnection.parse_win_events,
                              f'-{fetch_hours}h',  # This log can be huge, please avoid changing this number
                              maximum_records_per_search,
                              'Windows Login',
                              send_object_to_raw=True)
        yield from self.fetch('search sourcetype="*cisco*" AND "BT PROCESS" AND "M="',
                              SplunkConnection.parse_cisco_bt,
                              earliest,
                              maximum_records_per_search,
                              'Cisco client BT PROCESS')
        yield from self.fetch('search index=inf_netauth AND "PulseSecure:" AND "NCIP"',
                              SplunkConnection.parse_vpn,
                              earliest,
                              1000,  # This repeats it very fast
                              'VPN')
        yield from self.fetch('search index=inf_netauth AND "FLOW_REASSEMBLE_SUCCEED"',
                              SplunkConnection.parse_vpn,
                              earliest,
                              1000,  # This repeats it very fast
                              'VPN')
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
