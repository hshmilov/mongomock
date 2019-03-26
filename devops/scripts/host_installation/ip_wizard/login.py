#!/usr/bin/env python3
import ipaddress
import os
# pylint: disable=deprecated-module
import string
import sys

INTERFACE_FILTER_LIST = ['lo', 'docker', 'veth', 'weave', 'datapath', 'vxlan']

TEMPLATE = '''
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto {0}
iface {0} inet static
'''

DHCP = '''
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto {0}
iface {0} inet dhcp
'''


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


def generate_static(interface):
    address = check_addr('Enter static ip addr (eg 192.168.1.10): ')
    netmask = check_addr('Enter netmask (eg 255.255.255.0): ')
    network = check_addr('Enter network (eg 192.168.1.0): ')
    gateway = check_addr('Enter gateway (eg 192.168.1.1): ')
    dns1 = check_addr('Enter dns-nameserver (eg 8.8.8.8 or empty): ')
    dns2 = check_addr('Enter secondary dns-nameserver (eg 8.8.8.8 or empty): ')
    domain = check_domain('Enter dns domain (eg somedomain.com or empty): ')

    res = TEMPLATE.format(interface)
    res += f'\taddress {address}\n'
    res += f'\tnetmask {netmask}\n'
    res += f'\tnetwork {network}\n'
    res += f'\tgateway {gateway}\n'
    res += f'\tdns-nameservers {dns1} {dns2}\n'
    if domain != '':
        res += f'\tdns-domain {domain}\n'
    return res + '\n'


def generate_interfaces(interface):
    conf_type = input('Enter interface type: [static/dhcp] or exit to abort: ')

    if conf_type == 'exit':
        sys.exit(1)

    if conf_type == 'dhcp':
        return DHCP.format(interface)

    if conf_type == 'static':
        return generate_static(interface)

    print(f'not supported configuration type {conf_type}')
    sys.exit(1)


def _represents_int(int_str):
    try:
        int(int_str)
        return True
    except ValueError:
        return False


def choose_interface():
    interface_list = os.listdir('/sys/class/net/')
    interface_list = [current_interface for current_interface in interface_list if
                      not any(current_interface.startswith(x) for x in INTERFACE_FILTER_LIST)]

    response = 0
    # print the interfaces to user.
    print('interface list:')
    for idx, val in enumerate(interface_list):
        print(f'({idx+1}) {val} ')

    while not _represents_int(response) or int(response) - 1 < 0 or int(response) - 1 > len(
            interface_list) - 1:
        response = input('Please enter interface number:')
    return interface_list[int(response) - 1]


def main():
    chosen_interface = choose_interface()
    interfaces = generate_interfaces(chosen_interface)

    print(f'Generated the following: \n{interfaces}\n')

    res = ''
    while res not in ['yes', 'no']:
        res = input('Apply changes? please type yes/no :')
        if res == 'yes':
            with open('/home/netconfig/interfaces', 'wb') as f:
                f.write(interfaces.encode())
            return sys.exit(0)
        if res == 'no':
            return sys.exit(1)


if __name__ == '__main__':
    main()
