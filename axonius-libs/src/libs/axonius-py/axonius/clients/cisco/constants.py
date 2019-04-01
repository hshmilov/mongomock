from collections import namedtuple


def strings_named_tuple(name, strings: tuple):
    nt = namedtuple(name, strings)
    return nt(**dict(zip(strings, strings)))


# snmp related

BASIC_INFO_OID_KEYS = (
    'system_description',
    'interface',
    'ip',
    'port_security',
    'port_security_entries',
    'device_model',
    'device_model2',
    'device_serial',
    'device_serial2',
    'base_mac',
)

OID_KEYS = ('arp', 'cdp') + BASIC_INFO_OID_KEYS

OIDS = namedtuple('oids', OID_KEYS)(
    arp='1.3.6.1.2.1.3.1.1.2',
    cdp='1.3.6.1.4.1.9.9.23.1.2',
    system_description='1.3.6.1.2.1.1',
    interface='1.3.6.1.2.1.2.2.1',
    ip='1.3.6.1.2.1.4.20',
    port_security='1.3.6.1.4.1.9.9.315.1.2.1.1',
    port_security_entries='1.3.6.1.4.1.9.9.315.1.2.2.1',
    device_model='1.3.6.1.4.1.9.5.1.2.16.0',
    device_model2='.1.3.6.1.2.1.47.1.1.1.1.13.1',
    device_serial='1.3.6.1.4.1.9.5.1.2.19.0',
    device_serial2='1.3.6.1.2.1.47.1.1.1.1.11.1',
    base_mac='1.3.6.1.2.1.17.1.1.0',
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

ARGUMENTS_KEYS = SNMP_ARGUMENTS_KEYS


ARGUMENTS = strings_named_tuple('arguments', ARGUMENTS_KEYS)
