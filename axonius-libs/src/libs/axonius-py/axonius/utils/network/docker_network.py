import ipaddress
import logging
import socket

from urllib3.util.url import parse_url

import netifaces

logger = logging.getLogger(f'axonius.{__name__}')

COLLISION_MESSAGE = 'ADDR_COLLISION_DETECTED'


def get_docker_ipv4_interface():
    # we have ['lo', 'eth0', 'ethwe'] and eth0 represents docker
    return netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]


def get_weave_ipv4_interface():
    # we have ['lo', 'eth0', 'ethwe'] and ethwe represents weave
    return netifaces.ifaddresses('ethwe')[netifaces.AF_INET][0]


def get_network_from_interface(iface: dict) -> ipaddress.IPv4Network:
    ip = iface['addr']
    mask = iface['netmask']
    return ipaddress.IPv4Network(f'{ip}/{mask}', strict=False)


def has_addr_collision(domain):
    try:

        docker_net = get_network_from_interface(get_docker_ipv4_interface())
        weaver_net = get_network_from_interface(get_weave_ipv4_interface())

        host_part_of_domain = parse_url(domain).host
        domain_ip = socket.gethostbyname(host_part_of_domain)
        domain_ip_net = ipaddress.IPv4Network(domain_ip)

        if docker_net.overlaps(domain_ip_net):
            return True, f'{domain_ip_net} overlapped with docker network {docker_net}'

        if weaver_net.overlaps(domain_ip_net):
            return True, f'{domain_ip_net} overlapped with weave network {weaver_net}'

    except Exception as e:
        logger.exception(f'failed to check collision for domain {domain} {netifaces.interfaces()} {e}')
        raise

    return False, 'No collision'
