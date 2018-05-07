import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.clients.cisco.abstract import *

from pysnmp.hlapi import *
from collections import defaultdict
import socket

ARP_OID = '.1.3.6.1.2.1.3.1.1.2'
CDP_OID = '.1.3.6.1.4.1.9.9.23.1.2'


def unpack_mac(s):
    return ("%02X:" * 6)[:-1] % tuple(map(ord, s))


def extract_ip_from_mib(mib):
    return '.'.join(str(mib).split('.')[-4:])


class CiscoSnmpClient(AbstractCiscoClient):
    def __init__(self, community, ip, port=161):
        super().__init__()

        self._community = community
        self._ip = ip
        self._port = port
        self._engine = SnmpEngine()

    def _next_cmd(self, oid):
        return nextCmd(self._engine,
                       CommunityData(self._community),
                       UdpTransportTarget((self._ip, self._port)),
                       ContextData(),
                       ObjectType(ObjectIdentity(oid)),
                       lexicographicMode=False)

    def _query_dhcp_leases(self):
        logger.warning('dhcp isn\'t implemented yet - skipping')
        yield from ()

    def _query_arp_table(self):
        for query_result in self._next_cmd(ARP_OID):
            try:
                # for now ignore errors
                # TODO: raise ClientConnectionError for creds error
                logger.info(f'my_result= {query_result}')
                error, _, _, result = query_result
                if error:
                    logger.error(f'Unable to query arp table for {self._ip} error: {error}')
                    continue
                yield SnmpArpCiscoData(result)
            except Exception as e:
                logger.exception('Exception while quering arp table')

    @staticmethod
    def _group_cdp(results):
        groups = defaultdict(list)
        for result in results:
            oid = result[0][0]
            groups[(oid[-1], oid[-2])].append(result)
        return groups.values()

    def _query_cdp_table(self):
        data = list(self._next_cmd(CDP_OID))
        # TODO: raise ClientConnectionError for creds error
        errors = list(map(lambda x: x[0], data))
        results = list(map(lambda x: x[3], data))
        if any(errors):
            logger.error(f'Unable to query cdp table for {self._ip} errors: {errors}')
            return []

        results = self._group_cdp(results)
        return list(map(lambda x: SnmpCdpCiscoData(x), results))


class SnmpArpCiscoData(ArpCiscoData):
    def parse(self):
        try:
            entry = self._raw_data
            ip = extract_ip_from_mib(entry[0][0])
            mac = unpack_mac(str(entry[0][1]))
            yield {'mac': mac, 'ip': ip}
        except Exception:
            logger.exception('Exception while parsing arp data')
            return


class SnmpCdpCiscoData(CdpCiscoData):

    @staticmethod
    def parse_unhandled(oid, value):
        logger.warning(f'Unhandled oid: {oid} value: {value}')

    @staticmethod
    def parse_ip(oid, value):
        return socket.inet_ntoa(bytes(value))

    @staticmethod
    def parse_version(oid, value):
        return str(value)

    @staticmethod
    def parse_device_id(oid, value):
        return str(value)

    @staticmethod
    def parse_platform(oid, value):
        return str(value)

    def parse(self):
        result = {}
        entries = self._raw_data
        for entry in entries:
            try:
                oid, value = entry[0][0], entry[0][1]
                parse_function, key = CDP_INFO_TABLE.get(oid[-3], (self.parse_unhandled, None))
                value = parse_function(oid, value)
                if key and value:
                    result[key] = value
            except Exception:
                logger.exception('Exception while parsing cdp data')
        yield result


CDP_INFO_TABLE = {
    4: (SnmpCdpCiscoData.parse_ip, 'IP address'),
    5: (SnmpCdpCiscoData.parse_version, 'Version'),
    6: (SnmpCdpCiscoData.parse_device_id, 'Device ID'),
    8: (SnmpCdpCiscoData.parse_platform, 'Platform'),
}

if __name__ == "__main__":
    a = list(CiscoSnmpClient('public', '80.55.163.190')._query_cdp_table())
    # print(a)
    #a=list(CiscoSnmpClient('public', '192.168.20.35')._query_cdp_table())
    b = list(map(lambda x: list(x.parse()), a))
    print(b)
    # for i in b:
    #    pprint.pprint(i)
    #    print('----')
    #list(map(lambda x: x.parse(), a))
