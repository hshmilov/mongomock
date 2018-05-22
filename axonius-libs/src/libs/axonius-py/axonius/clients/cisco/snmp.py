import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.clients.cisco.abstract import *
from axonius.clients.cisco import snmp_parser

from pysnmp.hlapi import *
from collections import defaultdict
from axonius.adapter_exceptions import ClientConnectionException


# snmp OID (object identifires) we use to query data
ARP_OID = '1.3.6.1.2.1.3.1.1.2'
CDP_OID = '1.3.6.1.4.1.9.9.23.1.2'


SYSTEM_DESCRIPTION_OID = '1.3.6.1.2.1.1'
INETFACE_OID = '1.3.6.1.2.1.2.2.1'
IP_OID = '1.3.6.1.2.1.4.20'


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
        self._next_cmd(SYSTEM_DESCRIPTION_OID + '.1.1.0')
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

    def _query_basic_info(self):
        ''' query basic information about the device itself '''
        data = list(self._next_cmd(SYSTEM_DESCRIPTION_OID))
        errors = list(map(lambda x: x[0], data))
        results = [('info', list(map(lambda x: x[3], data)))]

        data = list(self._next_cmd(INETFACE_OID))
        errors += list(map(lambda x: x[0], data))
        results += [('iface', list(map(lambda x: x[3], data)))]

        data = list(self._next_cmd(IP_OID))
        errors += list(map(lambda x: x[0], data))
        results += [('ip', list(map(lambda x: x[3], data)))]

        if any(errors):
            logger.error(f'Unable to query basic info table for {self._ip} errors: {errors}')
            return None

        return SnmpBasicInfoCiscoData(results)

    # TODO: move to CdpCiscoData
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


class SnmpBasicInfoCiscoData(BasicInfoData):

    def _parse_basic_info(self, entries):
        for entry in entries:
            try:
                oid, value = entry[0][0], entry[0][1]
                key, value = SystemDescriptionTable.parse_value(oid, value)
                if value is not None:
                    self.result[key] = value
            except Exception:
                logger.exception('Exception while parsing basic info')

    def _group_iface(self, entries):
        groups = defaultdict(list)
        for result in entries:
            oid = result[0][0]
            groups[oid[-1]].append(result)
        return groups.values()

    def _parse_iface(self, entries):
        self.result['ifaces'] = {}
        for group in self._group_iface(entries):
            iface = {}
            for entry in group:
                try:
                    oid, value = entry[0][0], entry[0][1]
                    key, value = IfaceTable.parse_value(oid, value)
                    if value is not None:
                        iface[key] = value
                except Exception:
                    logger.exception('Exception while parsing basic info iface')
                    continue
            if iface.get('index'):
                self.result['ifaces'][iface.get('index')] = iface

    def _parse_ip(self, entires):
        ips = defaultdict(dict)
        for entry in entires:
            try:
                oid, value = entry[0][0], entry[0][1]
                oid, ip = oid[:-4], snmp_parser.extract_ip_from_mib(oid)
                key, value = IPTable.parse_value(oid, value)
                if value:
                    ips[ip][key] = value
            except Exception:
                logger.exception('Exception while parsing basic info ip')
                continue
        for value in ips.values():
            index = value.get('index')
            if index in self.result['ifaces'].keys():
                if 'ips' not in self.result['ifaces'][index]:
                    self.result['ifaces'][index]['ips'] = []
                self.result['ifaces'][index]['ips'].append(value)

    def _parse(self):
        self.result = {'device_mode': 'cisco'}
        for type_, entries in self._raw_data:
            if type_ == "info":
                self._parse_basic_info(entries)
            if type_ == "iface":
                self._parse_iface(entries)
            if type_ == "ip":
                self._parse_ip(entries)

        yield self.result


class SnmpArpCiscoData(ArpCiscoData):
    def _parse(self):
        for entry in self._raw_data:
            try:
                ip = snmp_parser.extract_ip_from_mib(entry[0][0])
                mac = snmp_parser.unpack_mac(entry[0][1])
                yield {'mac': mac, 'ip': ip}
            except Exception:
                logger.exception('Exception while parsing arp data')


class SnmpCdpCiscoData(CdpCiscoData):

    def _parse(self):
        for entries in self._raw_data:
            result = {}
            for entry in entries:
                try:
                    oid, value = entry[0][0], entry[0][1]
                    key, value = CdpTable.parse_value(oid, value)
                    if value is not None:
                        result[key] = value
                except Exception:
                    logger.exception('Exception while parsing cdp data')
            yield result


class CdpTable(snmp_parser.SnmpTable):
    table = {
        4: (snmp_parser.parse_ip, 'ip'),
        5: (snmp_parser.parse_str, 'version'),
        6: (snmp_parser.parse_str, 'hostname'),
        7: (snmp_parser.parse_str, 'iface'),
        8: (snmp_parser.parse_str, 'device_model'),
    }
    index = -3


class SystemDescriptionTable(snmp_parser.SnmpTable):
    table = {
        1: (snmp_parser.parse_str, 'version'),
        3: (snmp_parser.parse_str, 'uptime'),
        4: (snmp_parser.parse_str, 'contact'),
        5: (snmp_parser.parse_str, 'hostname'),
        6: (snmp_parser.parse_str, 'location'),
    }
    index = -2


class IfaceTable(snmp_parser.SnmpTable):
    table = {
        1: (snmp_parser.parse_str, 'index'),
        2: (snmp_parser.parse_str, 'descritption'),
        3: (snmp_parser.parse_str, 'type'),
        4: (snmp_parser.parse_str, 'mtu'),
        5: (snmp_parser.parse_str, 'speed'),
        6: (snmp_parser.parse_mac, 'mac'),
        7: (snmp_parser.parse_str, 'admin-status'),
        8: (snmp_parser.parse_str, 'operation-status'),
    }
    index = -2


class IPTable(snmp_parser.SnmpTable):
    table = {
        1: (snmp_parser.parse_ip, 'address'),
        2: (snmp_parser.parse_str, 'index'),
        3: (snmp_parser.parse_ip, 'net-mask'),
    }
    index = -1


if __name__ == "__main__":
    import pprint
    import logging
    from logging import info, warning, debug, error

    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
    a = CiscoSnmpClient(host='xxx', community='xxx', port=161)._query_basic_info()
    b = a.get_parsed_data()
    pprint.pprint(b)
