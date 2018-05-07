#!/usr/bin/env python3
import sys
import ipaddress
import string

template = """
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto ens33
iface ens33 inet static
"""

dhcp = """
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto ens33
iface ens33 inet dhcp
"""


def check_addr(message):
    while True:
        try:
            addr = input(message)
            if addr == '':
                return addr
            return str(ipaddress.ip_address(addr))
        except Exception:
            print(f'Invalid addr {addr}')


def check_domain(message):
    while True:
        try:
            domain = input(message)
            for ch in domain:
                if ch not in string.digits + string.ascii_letters + '-._/\\':
                    print(f'Illegal character {ch} in domain name')
                    raise Exception()

            return domain
        except Exception:
            pass


def generate_static():
    address = check_addr('Enter static ip addr (eg 192.168.1.10): ')
    netmask = check_addr('Enter netmask (eg 255.255.255.0): ')
    network = check_addr('Enter network (eg 192.168.1.0): ')
    gateway = check_addr('Enter gateway (eg 192.168.1.1): ')
    dns1 = check_addr('Enter dns-nameserver (eg 8.8.8.8 or empty): ')
    dns2 = check_addr('Enter secondary dns-nameserver (eg 8.8.8.8 or empty): ')
    domain = check_domain('Enter dns domain (eg somedomain.com or empty): ')

    res = template
    res += f'\taddress {address}\n'
    res += f'\tnetmask {netmask}\n'
    res += f'\tnetwork {network}\n'
    res += f'\tgateway {gateway}\n'
    res += f'\tdns-nameservers {dns1} {dns2}\n'
    if domain != '':
        res += f'\tdns-domain {domain}\n'
    return res + "\n"


def generate_interfaces():
    conf_type = input('Enter interface type: [static/dhcp] or exit to abort: ')

    if conf_type == 'exit':
        sys.exit(1)

    if conf_type == 'dhcp':
        return dhcp

    if conf_type == 'static':
        return generate_static()

    print(f'not supported configuration type {conf_type}')
    sys.exit(1)


def main():
    interfaces = generate_interfaces()

    print(f'Generated the following: \n{interfaces}\n')

    res = ""
    while res not in ['yes', 'no']:
        res = input("Apply changes? please type yes/no :")
        if res == 'yes':
            with open('/home/netconfig/interfaces', 'wb') as f:
                f.write(interfaces.encode())
            return sys.exit(0)
        if res == 'no':
            return sys.exit(1)


if __name__ == '__main__':
    main()
