import logging
logger = logging.getLogger(f'axonius.{__name__}')

from pysnmp.hlapi import *

ARP_OID = '.1.3.6.1.2.1.3.1.1.2'


def unpack_mac(s):
    return ("%02x:" * 6)[:-1] % tuple(map(ord, s))


def extract_ip_from_mib(mib):
    return '.'.join(str(mib).split('.')[-4:])


class CiscoSnmpClient:
    def __init__(self, community, ip, port):
        self._community = community
        self._ip = ip
        self._port = port
        self._engine = SnmpEngine()

    def _query_arp_table(self):
        return nextCmd(self._engine,
                       CommunityData(self._community),
                       UdpTransportTarget((self._ip, self._port)),
                       ContextData(),
                       ObjectType(ObjectIdentity(ARP_OID)),
                       lexicographicMode=False)

    def query_arp_table(self):
        for query_result in self._query_arp_table():
            try:
                # for now ignore errors
                logger.info(f'my_result= {query_result}')
                error, _, _, result = query_result
                if error:
                    logging.error(f'Unable to query arp table for {self._ip} error: {error}')
                    continue
                yield extract_ip_from_mib(result[0][0]), unpack_mac(str(result[0][1]))
            except Exception as e:
                logger.exception('Exception while quering arp table')
