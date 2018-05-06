import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.clients.cisco.abstract import AbstractCiscoClient, ArpCiscoData

from pysnmp.hlapi import *

ARP_OID = '.1.3.6.1.2.1.3.1.1.2'


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

    def __query_arp_table(self):
        return nextCmd(self._engine,
                       CommunityData(self._community),
                       UdpTransportTarget((self._ip, self._port)),
                       ContextData(),
                       ObjectType(ObjectIdentity(ARP_OID)),
                       lexicographicMode=False)

    def _query_dhcp_leases():
        logging.warning('dhcp isn\'t implemented yet - skipping')
        yield from ()

    def _query_arp_table(self):
        for query_result in self.__query_arp_table():
            try:
                # for now ignore errors
                # TODO: raise ClientConnectionError for creds error
                logger.info(f'my_result= {query_result}')
                error, _, _, result = query_result
                if error:
                    logging.error(f'Unable to query arp table for {self._ip} error: {error}')
                    continue
                yield SnmpArpCiscoData(result)
            except Exception as e:
                logger.exception('Exception while quering arp table')


class SnmpArpCiscoData(ArpCiscoData):

    def parse(self):
        entry = self._raw_data
        ip = extract_ip_from_mib(entry[0][0])
        mac = unpack_mac(str(entry[0][1]))
        yield {'mac': mac, 'ip': ip}
