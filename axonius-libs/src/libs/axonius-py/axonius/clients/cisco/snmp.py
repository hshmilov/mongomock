import asyncio
import logging
from collections import defaultdict

from pyasn1.type.univ import Null
from pysnmp.hlapi.asyncio import (CommunityData, ContextData, ObjectIdentity,
                                  ObjectType, SnmpEngine)
from pysnmp.hlapi.asyncio import UdpTransportTarget as AsyncUdpTransportTarget
from pysnmp.hlapi.asyncio import bulkCmd
from pysnmp.hlapi.varbinds import CommandGeneratorVarBinds

from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.singleton import Singleton
from axonius.clients.cisco import snmp_parser
from axonius.clients.cisco.abstract import (AbstractCiscoClient, ArpCiscoData,
                                            BasicInfoData, CdpCiscoData)

logger = logging.getLogger(f'axonius.{__name__}')


# snmp OID (object identifires) we use to query data
ARP_OID = '1.3.6.1.2.1.3.1.1.2'
CDP_OID = '1.3.6.1.4.1.9.9.23.1.2'


SYSTEM_DESCRIPTION_OID = '1.3.6.1.2.1.1'
INETFACE_OID = '1.3.6.1.2.1.2.2.1'
IP_OID = '1.3.6.1.2.1.4.20'


class SingletonEngine(metaclass=Singleton):
    def __init__(self):
        self.engine = None

    def get_instance(self):
        if not self.engine:
            self.engine = SnmpEngine()
        return self.engine

    def close_instance(self):
        dispatcher = self.engine.transportDispatcher
        if dispatcher:
            dispatcher.closeDispatcher()
        self.engine = None


def run_event_loop(tasks):
    SingletonEngine().get_instance()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    tasks, _ = loop.run_until_complete(asyncio.wait(tasks))
    SingletonEngine().close_instance()
    return map(lambda x: x.result(), tasks)


async def asyncio_next(engine, community, ip, port, oid):
    # based on hlapi/asyncore/sync/cmdgen.py NextCmd

    varBinds = [ObjectType(ObjectIdentity(oid))]
    results = []
    initialVars = CommandGeneratorVarBinds().makeVarBinds(engine, [ObjectType(ObjectIdentity(oid))])[0]

    while True:
        # XXX: fallback to nextCmd
        (errorIndication,
         errorStatus,
         errorIndex,
         varBindTable) = await bulkCmd(
             engine,
             CommunityData(community),
             AsyncUdpTransportTarget((ip, port)),
             ContextData(),
             0, 500,
             *varBinds,
             lookupMib=False)

        if errorIndication:
            results.append((errorIndication, errorStatus, errorIndex, varBindTable))
            return results

        if errorStatus:
            if errorStatus == 2:
                # Hide SNMPv1 noSuchName error which leaks in here
                # from SNMPv1 Agent through internal pysnmp proxy.
                errorStatus = errorStatus.clone(0)
                errorIndex = errorIndex.clone(0)
            results.append((errorIndication, errorStatus, errorIndex, varBindTable))
            return results

        for varBinds in varBindTable:
            for idx, varBind in enumerate(varBinds):
                name, val = varBind
                if not isinstance(val, Null):
                    if not initialVars[idx].isPrefixOf(name):
                        return results
                    results.append((errorIndication, errorStatus, errorIndex, varBinds))
                    break
            else:
                return results
        varBinds = [ObjectType(ObjectIdentity(varBinds[0][0]))]


class CiscoSnmpClient(AbstractCiscoClient):
    def __init__(self, **kwargs):
        super().__init__()
        for required_arg in ('host', 'community', 'port'):
            if required_arg not in kwargs:
                raise ClientConnectionException(f'SNMP - missing required parmeter "{required_arg}"')

        self._community = kwargs['community']
        self._ip = kwargs['host']
        self._port = kwargs['port']

    def validate_connection(self):
        data = list(self._next_cmd(SYSTEM_DESCRIPTION_OID + '.1'))[0]
        if not data:
            raise ClientConnectionException(f'Unable to communicate with {self._ip} data: {data}')

        errors = [x[0] for x in data]
        results = [x[3] for x in data]

        if any(errors) or not results:
            raise ClientConnectionException(f'Unable to communicate with {self._ip}' +
                                            f' errors: {errors}, results: {results}')

    def _next_cmd(self, oid):
        return run_event_loop([self._async_next_cmd(oid)])

    async def _async_next_cmd(self, oid):
        engine = SingletonEngine().get_instance()
        data = await asyncio_next(engine, self._community,
                                  self._ip, self._port,
                                  oid)
        return data

    async def _query_dhcp_leases(self):
        logger.debug('dhcp isn\'t implemented yet - skipping')
        return None

    async def _query_arp_table(self):
        results = []
        for query_result in await self._async_next_cmd(ARP_OID):
            try:
                error, _, _, result = query_result
                if error:
                    logger.error(f'Unable to query arp table for {self._ip} error: {error}')
                    continue
                results.append(result)
            except Exception as e:
                logger.exception('Exception while quering arp table')
        return SnmpArpCiscoData(results, received_from=self._ip)

    async def _query_basic_info(self):
        """ query basic information about the device itself """
        data = await self._async_next_cmd(SYSTEM_DESCRIPTION_OID)
        errors = list(map(lambda x: x[0], data))
        results = [('info', list(map(lambda x: x[3], data)))]

        data = await self._async_next_cmd(INETFACE_OID)
        errors += list(map(lambda x: x[0], data))
        results += [('iface', list(map(lambda x: x[3], data)))]

        data = await self._async_next_cmd(IP_OID)
        errors += list(map(lambda x: x[0], data))
        results += [('ip', list(map(lambda x: x[3], data)))]

        if any(errors):
            logger.error(f'Unable to query basic info table for {self._ip} errors: {errors}')
            return None

        return SnmpBasicInfoCiscoData(results)

    # XXX: move to CdpCiscoData
    @staticmethod
    def _group_cdp(results):
        groups = defaultdict(list)
        for result in results:
            oid = result[0][0]
            groups[(oid[-1], oid[-2])].append(result)
        return groups.values()

    async def _query_cdp_table(self):
        data = await self._async_next_cmd(CDP_OID)
        errors = list(map(lambda x: x[0], data))
        results = list(map(lambda x: x[3], data))
        if any(errors):
            logger.error(f'Unable to query cdp table for {self._ip} errors: {errors}')
            return None

        results = self._group_cdp(results)
        return SnmpCdpCiscoData(results, received_from=self._ip)

    def get_tasks(self):
        """ return all tasks """
        return [
            self._query_basic_info(),
            self._query_cdp_table(),
            self._query_arp_table(),
            self._query_dhcp_leases()
        ]

    def query_all(self):
        """ since snmp queries are async, we must handle them differently """
        tasks = self.get_tasks()
        yield from run_event_loop(tasks)


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

    @staticmethod
    def _group_iface(entries):
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
            if type_ == 'info':
                self._parse_basic_info(entries)
            if type_ == 'iface':
                self._parse_iface(entries)
            if type_ == 'ip':
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
        2: (snmp_parser.parse_str, 'description'),
        3: (snmp_parser.parse_str, 'type'),
        4: (snmp_parser.parse_str, 'mtu'),
        5: (snmp_parser.parse_str, 'speed'),
        6: (snmp_parser.parse_mac, 'mac'),
        7: (snmp_parser.parse_admin, 'admin-status'),
        8: (snmp_parser.parse_operational, 'operation-status'),
    }
    index = -2


class IPTable(snmp_parser.SnmpTable):
    table = {
        1: (snmp_parser.parse_ip, 'address'),
        2: (snmp_parser.parse_str, 'index'),
        3: (snmp_parser.parse_ip, 'net-mask'),
    }
    index = -1


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO)
    CLIENT = CiscoSnmpClient(host='XXX', community='public', port=161)
    CLIENT.validate_connection()
