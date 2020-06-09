from collections import namedtuple

from pysnmp.hlapi import (usm3DESEDEPrivProtocol, usmAesCfb128Protocol,
                          usmAesCfb192Protocol, usmAesCfb256Protocol,
                          usmDESPrivProtocol, usmHMAC128SHA224AuthProtocol,
                          usmHMAC192SHA256AuthProtocol,
                          usmHMAC256SHA384AuthProtocol,
                          usmHMAC384SHA512AuthProtocol, usmHMACMD5AuthProtocol,
                          usmHMACSHAAuthProtocol, usmNoAuthProtocol,
                          usmNoPrivProtocol)

VLAN_ID = 'vlan_id'
VLAN_NAME = 'vlan_name'
VOICE_VLAN = 'voice_vlan'


# snmp related
BASIC_INFO_OID_KEYS = (
    'system_description',
    'interface',
    'ip',
    'port_security',
    'port_security_entries',
    'port_security_vlan_entries',
    'port_access',
    'device_model',
    'device_model2',
    'device_model3',
    'device_serial',
    'device_serial2',
    'device_serial3',
    'base_mac',
    'vlans',
    'voice_vlan',
    'vtp_vlans'

)

SNMP_OID_KEYS = (
    'arp_legacy',
    'arp',
    'cdp',
)

OID_KEYS = SNMP_OID_KEYS + BASIC_INFO_OID_KEYS

OIDS = namedtuple('oids', OID_KEYS)(
    arp_legacy='1.3.6.1.2.1.3.1.1.2',
    arp='1.3.6.1.2.1.4.22.1.2',
    cdp='1.3.6.1.4.1.9.9.23.1.2',
    system_description='1.3.6.1.2.1.1',
    interface='1.3.6.1.2.1.2.2.1',
    ip='1.3.6.1.2.1.4.20',
    port_security='1.3.6.1.4.1.9.9.315.1.2.1.1',
    port_security_entries='1.3.6.1.4.1.9.9.315.1.2.2.1',
    port_security_vlan_entries='1.3.6.1.4.1.9.9.315.1.2.3.1',
    port_access='1.3.6.1.4.1.9.9.220.1.1',
    device_model='1.3.6.1.4.1.9.5.1.2.16.0',
    device_model2='.1.3.6.1.2.1.47.1.1.1.1.13.1',
    device_model3='.1.3.6.1.2.1.47.1.1.1.1.13',  # table of models
    device_serial='1.3.6.1.4.1.9.5.1.2.19.0',
    device_serial2='1.3.6.1.2.1.47.1.1.1.1.11.1',
    device_serial3='1.3.6.1.2.1.47.1.1.1.1.11',  # table of serials
    base_mac='1.3.6.1.2.1.17.1.1.0',
    vtp_vlans='1.3.6.1.4.1.9.9.46.1.3.1.1.4',
    vlans='1.3.6.1.4.1.9.9.68.1.2.2.1',  # vmMembershipTable
    voice_vlan='1.3.6.1.4.1.9.9.68.1.5.1.1'  # vmVoiceVlanTable

)


def get_oid_name(oid):
    return OID_KEYS[OIDS.index(oid)]

# console


COMMANDS_KEYS = ('arp',
                 'cdp',
                 'dhcp')

Commands = namedtuple('commands', COMMANDS_KEYS)
COMMANDS = Commands(
    arp='show arp',
    cdp='show cdp neighbors detail',
    dhcp='show ip dhcp binding'
)


def get_command_name(command):
    return COMMANDS_KEYS[COMMANDS.index(command)]

# arguments


SNMP_ARGUMENTS_KEYS = ('community', 'host', 'port')

SNMPV3_ARGUMENTS_KEYS = ('username',
                         'priv_protocol',
                         'auth_protocol',
                         'host',
                         'port',
                         'secure_level')

SNMPV3_KEY_AUTH = 'auth_passphrase'
SNMPV3_KEY_PRIV = 'priv_passphrase'

AuthProtocols = namedtuple('authprotocols', ('hmac_md5',
                                             'hmac_sha1',
                                             'hmac128_sha224',
                                             'hmac128_sha256',
                                             'hmac256_sha384',
                                             'hmac384_sha512',
                                             'no_auth'))
AUTH_PROTOCOLS = AuthProtocols(
    hmac_md5=usmHMACMD5AuthProtocol,
    hmac_sha1=usmHMACSHAAuthProtocol,
    hmac128_sha224=usmHMAC128SHA224AuthProtocol,
    hmac128_sha256=usmHMAC192SHA256AuthProtocol,
    hmac256_sha384=usmHMAC256SHA384AuthProtocol,
    hmac384_sha512=usmHMAC384SHA512AuthProtocol,
    no_auth=usmNoAuthProtocol)

PrivProtocols = namedtuple('privprotocols', ('des',
                                             'threedes',
                                             'aescfb128',
                                             'aescfb192',
                                             'aescfb256',
                                             'no_priv'))

PRIV_PROTOCOLS = PrivProtocols(
    des=usmDESPrivProtocol,
    threedes=usm3DESEDEPrivProtocol,
    aescfb128=usmAesCfb128Protocol,
    aescfb192=usmAesCfb192Protocol,
    aescfb256=usmAesCfb256Protocol,
    no_priv=usmNoPrivProtocol)

SECURITY_LEVELS = ('noAuthNoPriv', 'authNoPriv', 'authPriv')
