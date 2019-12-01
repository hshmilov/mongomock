import asyncio
import binascii
import logging
from collections import defaultdict, namedtuple

from pyasn1.type.univ import Null
from pysnmp.hlapi.asyncio import (CommunityData, ContextData, ObjectIdentity,
                                  ObjectType, SnmpEngine)
from pysnmp.hlapi.asyncio import UdpTransportTarget as AsyncUdpTransportTarget
from pysnmp.hlapi.asyncio import UsmUserData, bulkCmd, getCmd
from pysnmp.hlapi.varbinds import CommandGeneratorVarBinds
from pysnmp.proto.rfc1905 import NoSuchInstance

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.cisco import snmp_parser
from axonius.clients.cisco.abstract import (AbstractCiscoClient, ArpCiscoData,
                                            BasicInfoData, CdpCiscoData)
from axonius.clients.cisco.constants import (AUTH_PROTOCOLS,
                                             BASIC_INFO_OID_KEYS, OIDS,
                                             PRIV_PROTOCOLS,
                                             SNMP_ARGUMENTS_KEYS,
                                             SNMPV3_ARGUMENTS_KEYS,
                                             get_oid_name)
from axonius.utils.singleton import Singleton

logger = logging.getLogger(f'axonius.{__name__}')


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


async def asyncio_next(engine, auth, ip, port, oid):
    # based on hlapi/asyncore/sync/cmdgen.py NextCmd

    varBinds = [ObjectType(ObjectIdentity(oid))]
    results = []
    initialVars = CommandGeneratorVarBinds().makeVarBinds(engine, [ObjectType(ObjectIdentity(oid))])[0]

    while True:
        # XXX: fallback to nextCmd
        (errorIndication, errorStatus, errorIndex, varBindTable) = await bulkCmd(
            engine,
            auth,
            AsyncUdpTransportTarget((ip, port)),
            ContextData(),
            0,
            500,
            *varBinds,
            lookupMib=False,
        )

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


async def asyncio_get(engine, auth, ip, port, oid):
    varBinds = [ObjectType(ObjectIdentity(oid))]
    (errorIndication, errorStatus, errorIndex, varBindTable) = await getCmd(
        engine, auth, AsyncUdpTransportTarget((ip, port)), ContextData(), *varBinds, lookupMib=False
    )
    return (errorIndication, errorStatus, errorIndex, varBindTable)


class AbstractSnmpClient(AbstractCiscoClient):
    def __init__(self, **kwargs):
        super().__init__()
        for required_arg in self.REQUIRED_ARGS:
            if required_arg not in kwargs or not kwargs[required_arg]:
                raise ClientConnectionException(f'{self.PROTOCOL} - missing required parameter "{required_arg}"')
            setattr(self, '_' + required_arg, kwargs[required_arg])

    @staticmethod
    def get_device_type():
        return 'cisco_ios_snmp'

    @staticmethod
    def test_rechability(host, port):
        raise NotImplementedError()

    def validate_connection(self):
        data = list(self._get_cmd(OIDS.system_description + '.1.0', oid_name='description'))[0]
        if not data:
            raise ClientConnectionException(f'Unable to communicate with {self._host}')

    def _next_cmd(self, oid, oid_name=None):
        return run_event_loop([self._async_next_cmd(oid, oid_name)])

    def _get_cmd(self, oid, oid_name=None):
        return run_event_loop([self._async_get_cmd(oid, oid_name)])

    def get_auth(self):
        raise NotImplementedError()

    async def __async_get(self, oid):
        engine = SingletonEngine().get_instance()
        auth = self.get_auth()
        return await asyncio_get(engine, auth, self._host, self._port, oid)

    async def __async_next(self, oid):
        engine = SingletonEngine().get_instance()
        auth = self.get_auth()
        return await asyncio_next(engine, auth, self._host, self._port, oid)

    async def _async_get_cmd(self, oid, oid_name=None):
        if oid_name is None:
            oid_name = get_oid_name(oid)
        try:
            data = await self.__async_get(oid)
            error = data[0]
            data = data[3]
            if error:
                logger.warning(f'{oid_name} returned error: {error}')
                return None
            if isinstance(data[0][1], NoSuchInstance):
                return None
            result = oid_name, data
            return result
        except Exception:
            logger.exception(f'Failed to query {oid_name}')
            return None

    async def _async_next_cmd(self, oid, oid_name=None):
        if oid_name is None:
            oid_name = get_oid_name(oid)
        try:
            data = await self.__async_next(oid)
            errors = list(filter(None, map(lambda x: x[0], data)))
            result = oid_name, list(map(lambda x: x[3], data))
            if not errors:
                return result
            logger.error(f'{oid_name} returned errors: {errors}')
        except Exception:
            logger.exception(f'Failed to query {oid_name}')
        return None

    async def _query_dhcp_leases(self):
        logger.debug('dhcp isn\'t implemented yet - skipping')
        return None

    async def _query_arp_table(self):
        results = await self._async_next_cmd(OIDS.arp)
        if results:
            name, results = results
        else:
            results = []
        return SnmpArpCiscoData(results, received_from=self._host)

    async def _query_basic_info(self):
        """ query basic information about the device itself """
        basic_info_routines = [
            self._async_next_cmd(OIDS.system_description),
            self._async_next_cmd(OIDS.interface),
            self._async_next_cmd(OIDS.ip),
            self._async_next_cmd(OIDS.port_security),
            self._async_next_cmd(OIDS.port_security_entries),
            self._async_next_cmd(OIDS.port_security_vlan_entries),
            self._async_next_cmd(OIDS.port_access),
            self._async_get_cmd(OIDS.device_model),
            self._async_get_cmd(OIDS.device_model2),
            self._async_get_cmd(OIDS.device_serial),
            self._async_get_cmd(OIDS.device_serial2),
            self._async_get_cmd(OIDS.base_mac),
        ]
        results = list(filter(None, [await routine for routine in basic_info_routines]))
        return SnmpBasicInfoCiscoData(results)

    # XXX: move to CdpCiscoData
    @staticmethod
    def _group_cdp(results):
        groups = defaultdict(list)
        for result in results:
            oid = result[0][0]
            groups[(oid[-1], oid[-2])].append(result)
        return list(groups.values())

    async def _query_cdp_table(self):
        results = await self._async_next_cmd(OIDS.cdp)
        if results:
            name, results = results
        else:
            results = []
        results = self._group_cdp(results)
        return SnmpCdpCiscoData(results, received_from=self._host)

    def get_tasks(self):
        """ return all tasks """
        return [self._query_basic_info(), self._query_cdp_table(), self._query_arp_table(), self._query_dhcp_leases()]

    def query_all(self):
        """ since snmp queries are async, we must handle them differently """
        tasks = self.get_tasks()
        yield from run_event_loop(tasks)


class CiscoSnmpClient(AbstractSnmpClient):
    REQUIRED_ARGS = SNMP_ARGUMENTS_KEYS
    PROTOCOL = 'SNMP'

    @staticmethod
    def test_rechability(host, port):
        raise NotImplementedError()

    def get_auth(self):
        return CommunityData(self._community)


class CiscoSnmpV3Client(AbstractSnmpClient):
    REQUIRED_ARGS = SNMPV3_ARGUMENTS_KEYS
    PROTOCOL = 'SNMPV3'

    @staticmethod
    def test_rechability(host, port):
        raise NotImplementedError()

    def get_auth(self):
        return UsmUserData(userName=self._username,
                           authKey=self._auth_passphrase or None,
                           privKey=self._priv_passphrase or None,
                           authProtocol=AUTH_PROTOCOLS._asdict().get(self._auth_protocol) or None,
                           privProtocol=PRIV_PROTOCOLS._asdict().get(self._priv_protocol) or None)


class SnmpBasicInfoCiscoData(BasicInfoData):
    def _parse_basic_info(self, entries):
        for entry in entries:
            try:
                oid, value = entry[0][0], entry[0][1]
                if oid[-1] != 0:
                    # we only want zero index
                    continue
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
        interface = get_oid_name(OIDS.interface)
        self.result[interface] = {}
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
                self.result[interface][iface.get('index')] = iface

    def _parse_port_security(self, entries):
        interface_field = get_oid_name(OIDS.interface)
        port_security_field = get_oid_name(OIDS.port_security)

        for group in self._group_iface(entries):
            port_security = {}
            index = str(group[0][0][0][-1])
            for entry in group:
                try:
                    oid, value = entry[0][0], entry[0][1]
                    key, value = CpsIfConfigTable.parse_value(oid, value)
                    if value is not None:
                        port_security[key] = value
                except Exception:
                    logger.exception('Exception while parsing basic info port security')
                    continue
            if index not in self.result[interface_field]:
                self.result[interface_field][index] = {}
            self.result[interface_field][index][port_security_field] = port_security

    def _parse_port_security_vlan_entries(self, entries):
        interface = get_oid_name(OIDS.interface)
        port_security = get_oid_name(OIDS.port_security)
        port_security_entries = {}
        for entry in entries:
            try:
                oid, value = entry[0][0], entry[0][1]
                print(oid, value)
                index = str(oid[-8])
                mac = snmp_parser.unpack_mac(tuple(oid[-7:-1]))
                vlan = snmp_parser.parse_vlan_secure_mac_vlan_id(oid, value)
                key, value = CpsIfVlanSecureMacAddrTable.parse_value(oid, value)
                if value is not None:
                    if index not in port_security_entries:
                        port_security_entries[index] = {}
                    if mac not in port_security_entries[index]:
                        port_security_entries[index][mac] = {}
                    port_security_entries[index][mac][key] = value
                if vlan:
                    port_security_entries[index][mac]['vlan_id'] = str(vlan)

            except Exception:
                logger.exception('Exception while parsing basic info port security')
                continue
        for index, entry in port_security_entries.items():
            if index in self.result[interface].keys():
                if port_security not in self.result[interface][index]:
                    self.result[interface][index][port_security] = {}
                self.result[interface][index][port_security]['entries'] = entry

    def _parse_port_security_entries(self, entries):
        interface = get_oid_name(OIDS.interface)
        port_security = get_oid_name(OIDS.port_security)
        port_security_entries = {}
        for entry in entries:
            try:
                oid, value = entry[0][0], entry[0][1]
                index = str(oid[-7])
                mac = snmp_parser.unpack_mac(tuple(oid[-6:]))
                key, value = CpsSecureMacAddressTable.parse_value(oid, value)
                if value is not None:
                    if index not in port_security_entries:
                        port_security_entries[index] = {}
                    if mac not in port_security_entries[index]:
                        port_security_entries[index][mac] = {}
                    port_security_entries[index][mac][key] = value
            except Exception:
                logger.exception('Exception while parsing basic info port security')
                continue

        for index, entry in port_security_entries.items():
            if index in self.result[interface].keys():
                if port_security not in self.result[interface][index]:
                    self.result[interface][index][port_security] = {}
                self.result[interface][index][port_security]['entries'] = entry

    def _parse_port_access(self, entries):
        interface = get_oid_name(OIDS.interface)
        port_access = get_oid_name(OIDS.port_access)
        prot_access_entries = {}
        for entry in entries:
            try:
                oid, value = entry[0][0], entry[0][1]
                index = str(oid[-1])
                key, value = CpaePortTable.parse_value(oid, value)
                if value is None:
                    continue
                if index in self.result[interface].keys():
                    if port_access not in self.result[interface][index]:
                        self.result[interface][index][port_access] = {}
                    self.result[interface][index][port_access][key] = value
            except Exception:
                logger.exception('Exception while parsing basic info port access')
                continue

    def _parse_ip(self, entires):
        interface_field = get_oid_name(OIDS.interface)
        ip_field = get_oid_name(OIDS.ip)
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
            if index in self.result[interface_field].keys():
                if ip_field not in self.result[interface_field][index]:
                    self.result[interface_field][index][ip_field] = []
                self.result[interface_field][index][ip_field].append(value)

    def _parse_base_mac(self, entries):
        self.result[get_oid_name(OIDS.base_mac)] = binascii.hexlify(bytes(entries[0][1])).decode()

    def _parse_serial(self, entries):
        self.result[get_oid_name(OIDS.device_serial)] = str(entries[0][1])

    def _parse_device_model(self, entries):
        self.result[get_oid_name(OIDS.device_model)] = str(entries[0][1])

    def _parse(self):
        parse_table = namedtuple('parse_table', BASIC_INFO_OID_KEYS)(
            system_description=self._parse_basic_info,
            interface=self._parse_iface,
            ip=self._parse_ip,
            port_security=self._parse_port_security,
            port_security_entries=self._parse_port_security_entries,
            port_security_vlan_entries=self._parse_port_security_vlan_entries,
            port_access=self._parse_port_access,
            device_model=self._parse_device_model,
            device_model2=self._parse_device_model,
            device_serial=self._parse_serial,
            device_serial2=self._parse_serial,
            base_mac=self._parse_base_mac,
        )

        self.result = defaultdict(dict, {'os': 'cisco'})
        for type_, entries in self._raw_data:
            try:
                parse_table._asdict()[type_](entries)
            except Exception:
                logger.exception(f'Failed to parse {type_} {entries}')
        yield dict(self.result)


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


class CpsIfConfigTable(snmp_parser.SnmpTable):
    table = {
        1: (snmp_parser.parse_bool, 'enabled'),
        2: (snmp_parser.parse_security_status, 'status'),
        3: (snmp_parser.parse_int, 'max_addr'),
        # 4: mac_addr count
        # 5: aging time
        # 6: aging type
        # 7: aging enabled
        8: (snmp_parser.parse_violation_action, 'violation_action'),
        9: (snmp_parser.parse_int, 'violation_count'),
        # 10: last mac address
        # 11: clear address
        # 14: clear mac address
        15: (snmp_parser.parse_bool, 'sticky'),
    }
    index = -2


class CpsSecureMacAddressTable(snmp_parser.SnmpTable):
    table = {
        2: (snmp_parser.parse_secure_mac_type, 'type'),
        3: (snmp_parser.parse_int, 'remaining_age')
    }
    index = 13


class CpsIfVlanSecureMacAddrTable(snmp_parser.SnmpTable):
    table = {
        2: (snmp_parser.parse_vlan_secure_mac_vlan_id, 'vlan'),
        3: (snmp_parser.parse_secure_mac_type, 'type'),
        4: (snmp_parser.parse_gauge32, 'remaining_age')
    }
    index = 13


class CpaePortTable(snmp_parser.SnmpTable):
    table = {
        # 1: multiple entries
        2: (snmp_parser.parse_int, 'port_mode'),
        3: (snmp_parser.parse_int, 'guest_vlan_number'),
        # 4: in guest vlan
        5: (snmp_parser.parse_bool, 'shutdown_timeout_enabled'),
        6: (snmp_parser.parse_int, 'auth_fail_vlan_number'),
        7: (snmp_parser.parse_int, 'operation_vlan_number'),
        8: (snmp_parser.parse_int, 'operation_vlan_type'),
        9: (snmp_parser.parse_int, 'auth_fail_max_attempts'),
    }
    index = -2
