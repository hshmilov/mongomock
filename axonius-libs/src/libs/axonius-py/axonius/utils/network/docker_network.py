import ipaddress
import json
import logging
import socket
import subprocess

from urllib3.util.url import parse_url

import netifaces

logger = logging.getLogger(f'axonius.{__name__}')

COLLISION_MESSAGE = 'ADDR_COLLISION_DETECTED'

ADDR = 'addr'
NETMASK = 'netmask'


def get_ipv4_interfaces():
    names = netifaces.interfaces()
    for ifname in names:
        iface = netifaces.ifaddresses(ifname).get(netifaces.AF_INET)
        if iface and len(iface) > 0:
            for network in iface:
                if ADDR in network and NETMASK in network:
                    yield ifname, network


def get_network_from_interface(iface: dict) -> ipaddress.IPv4Network:
    ip = iface['addr']
    mask = iface['netmask']
    return ipaddress.IPv4Network(f'{ip}/{mask}', strict=False)


def has_addr_collision(domain):
    try:

        for ifname, iface in get_ipv4_interfaces():

            net = get_network_from_interface(iface)

            host_part_of_domain = parse_url(domain).host
            domain_ip = socket.gethostbyname(host_part_of_domain)
            domain_ip_net = ipaddress.IPv4Network(domain_ip)

            if net.overlaps(domain_ip_net):
                return True, f'{domain_ip_net} overlapped with network {net} {ifname}:{netifaces.ifaddresses(ifname)}'

    except Exception as e:
        logger.exception(f'failed to check collision for domain {domain} {netifaces.interfaces()} {e}')
        raise

    return False, 'No collision'


def read_weave_network_range():
    report = subprocess.check_output('weave report'.split())
    report = json.loads(report)
    weave_netrowk_range = report['IPAM']['Range']
    return weave_netrowk_range
