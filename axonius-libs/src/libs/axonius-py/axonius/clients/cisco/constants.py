from collections import namedtuple

OID_KEYS = ('arp',
            'cdp',
            'system_description',
            'interface',
            'ip',
            'port_security',
            'port_security_entries',
            'device_model',
            'device_serial')

Oids = namedtuple('oids', OID_KEYS)

OIDS = Oids(arp='1.3.6.1.2.1.3.1.1.2',
            cdp='1.3.6.1.4.1.9.9.23.1.2',
            system_description='1.3.6.1.2.1.1',
            interface='1.3.6.1.2.1.2.2.1',
            ip='1.3.6.1.2.1.4.20',
            port_security='1.3.6.1.4.1.9.9.315.1.2.1.1',
            port_security_entries='1.3.6.1.4.1.9.9.315.1.2.2.1',
            device_model='1.3.6.1.4.1.9.5.1.2.16.0',
            device_serial='1.3.6.1.4.1.9.5.1.2.19.0')
