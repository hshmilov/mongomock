import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.clients.cisco.abstract import *

from pysnmp.hlapi import *
from collections import defaultdict
import socket
from axonius.adapter_exceptions import ClientConnectionException

ARP_OID = '.1.3.6.1.2.1.3.1.1.2'
CDP_OID = '.1.3.6.1.4.1.9.9.23.1.2'
SYSTEM_DESCRIPTION_OID = '1.3.6.1.2.1.1.1.0'


def unpack_mac(s):
    return ("%02X:" * 6)[:-1] % tuple(map(ord, s))


def extract_ip_from_mib(mib):
    return '.'.join(str(mib).split('.')[-4:])


class CiscoSnmpClient(AbstractCiscoClient):
    def __init__(self, **kwargs):
        super().__init__()
        for required_arg in ('host', 'community', 'port'):
            if required_arg not in kwargs:
                raise ClientConnectionException(f'SNMP - missing required parmeter "{required_arg}"')

        self._community = kwargs['community']
        self._ip = kwargs['host']
        self._port = kwargs['port']
        self._engine = SnmpEngine()

    def _next_cmd(self, oid):
        return nextCmd(self._engine,
                       CommunityData(self._community),
                       UdpTransportTarget((self._ip, self._port)),
                       ContextData(),
                       ObjectType(ObjectIdentity(oid)),
                       lexicographicMode=False)

    def __enter__(self):
        """ Snmp is a connection-less protocol.
            So in order to simulate connection - we are going to get one mib and check for errors"""
        super().__enter__()
        self._next_cmd(SYSTEM_DESCRIPTION_OID)
        data = list(self._next_cmd(CDP_OID))
        errors = list(map(lambda x: x[0], data))
        if any(errors):
            raise ClientConnectionException(f'Unable to query system description errors: {errors}')
        return self

    def _query_dhcp_leases(self):
        logger.warning('dhcp isn\'t implemented yet - skipping')
        return None

    def _query_arp_table(self):
        results = []
        for query_result in self._next_cmd(ARP_OID):
            try:
                logger.info(f'my_result= {query_result}')
                error, _, _, result = query_result
                if error:
                    logger.error(f'Unable to query arp table for {self._ip} error: {error}')
                    continue
                results.append(result)
            except Exception as e:
                logger.exception('Exception while quering arp table')
        return SnmpArpCiscoData(results)

    @staticmethod
    def _group_cdp(results):
        groups = defaultdict(list)
        for result in results:
            oid = result[0][0]
            groups[(oid[-1], oid[-2])].append(result)
        return groups.values()

    def _query_cdp_table(self):
        data = list(self._next_cmd(CDP_OID))
        errors = list(map(lambda x: x[0], data))
        results = list(map(lambda x: x[3], data))
        if any(errors):
            logger.error(f'Unable to query cdp table for {self._ip} errors: {errors}')
            return None

        results = self._group_cdp(results)
        return SnmpCdpCiscoData(results)


class SnmpArpCiscoData(ArpCiscoData):
    def _parse(self):
        for entry in self._raw_data:
            try:
                ip = extract_ip_from_mib(entry[0][0])
                mac = unpack_mac(str(entry[0][1]))
                yield {'mac': mac, 'ip': ip}
            except Exception:
                logger.exception('Exception while parsing arp data')


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

    @staticmethod
    def parse_port_id(oid, value):
        return str(value)

    def _parse(self):
        for entries in self._raw_data:
            result = {}
            for entry in entries:
                try:
                    oid, value = entry[0][0], entry[0][1]
                    parse_function, key = CDP_INFO_TABLE.get(oid[-3], (self.parse_unhandled, None))
                    if not value:
                        logging.info(f'{oid} skipping empty value {key}')
                        continue
                    value = parse_function(oid, value)
                    if key and value:
                        result[key] = value
                except Exception:
                    logger.exception('Exception while parsing cdp data')
            yield result


CDP_INFO_TABLE = {
    4: (SnmpCdpCiscoData.parse_ip, 'ip'),
    5: (SnmpCdpCiscoData.parse_version, 'version'),
    6: (SnmpCdpCiscoData.parse_device_id, 'hostname'),
    7: (SnmpCdpCiscoData.parse_port_id, 'iface'),
    8: (SnmpCdpCiscoData.parse_platform, 'device_model'),
}

if __name__ == "__main__":
    import pprint
    import logging
    from logging import info, warning, debug, error

    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
    a = CiscoSnmpClient('public', 'x.x.x.x')._query_cdp_table()
    b = a.get_parsed_data()
    pprint.pprint(b)
