import dns.resolver
from dns.exception import DNSException
from axonius.adapter_exceptions import *
import socket


def query_dns(name_to_query, timeout, dns_server=None):
    """ Queries the dns server for a specific name
    :param name_to_query: The name we want to query
    :param timeout: Time to wait in case dns server doesnt answer
    :param dns_server: The ip address of the dns server. If none is given, the function will use the default
                       dns server of the machine
    :return: Ip address of the wanted device
    :raise NoIpFoundError: In case no ip was found for this device
    """
    my_res = dns.resolver.Resolver()
    my_res.timeout = timeout
    my_res.lifetime = timeout
    if dns_server is not None:  # If dns_server is none we will just use the default dns server
        my_res.nameservers = [dns_server]
    try:
        answer = my_res.query(name_to_query, 'A')
    except DNSException:
        raise NoIpFoundError()
    except Exception as e:
        raise NoIpFoundError(str(e))

    for rdata in answer:
        try:
            proposed_ip = str(rdata)
            socket.inet_aton(proposed_ip)
        except socket.error:
            continue
        return proposed_ip

    raise NoIpFoundError()
