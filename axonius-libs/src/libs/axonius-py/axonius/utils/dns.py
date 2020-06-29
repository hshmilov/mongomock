import asyncio
import socket
from inspect import isawaitable
from typing import List, Tuple, Union
import aiodns
import dns.resolver
from dns.exception import DNSException
from axonius.adapter_exceptions import NoIpFoundError


async def async_query_dns(loop: asyncio.AbstractEventLoop, hostname: str,
                          nameservers: List[str], timeout: float):
    """
    Dns query using aiodns
    :param loop: asyncio event loop
    :param hostname: hostname to resolve
    :param nameservers: dns nameservers to query
                        if nameserver item is none: query the default nameserver
    :param timeout: dns request timeout
    :return: dns response
    """
    if nameservers == [None]:
        nameservers = None
    resolver = aiodns.DNSResolver(loop=loop, timeout=timeout, nameservers=nameservers)
    # aiodns timeout bug https://github.com/saghul/aiodns/pull/64
    response = await asyncio.wait_for(resolver.query(hostname, 'A'), timeout)
    return response


# pylint: disable =R0912
async def query_dns_servers(loop: asyncio.AbstractEventLoop, hostname: Union[str, list],
                            nameservers: List[str],
                            timeout: float, greedy: bool,
                            fallback_to_default=True, callback=None) -> List[Tuple[str, List]]:
    """
    :param fallback_to_default: fallback to default dns server in case of dns failure
    :param loop: asyncio event loop
    :param hostname: hostname to resolve
    :param nameservers: dns nameservers to query
    :param timeout: dns request timeout
    :param greedy: if True - return the dns responses from all the given nameservers.
                    otherwise return only the response from the first dns server that resolves this hostname.
    :param callback: callback to call after the dns query
            callback signature: callback(loop: asyncio.AbstractEventLoop, hostname: str, results: list)
    :return: list of dns results tuple -> (resolved_ip, resolving_nameserver)
    """

    if isinstance(hostname, list):
        hostnames = hostname
    else:
        hostnames = [str(hostname)]

    results = []
    if greedy:
        for host in hostnames:
            for server in nameservers:
                try:
                    response = await async_query_dns(loop, host, [server, ], timeout)
                    results.append((response[0].host, [server, ]))
                except Exception:
                    continue
    else:
        try:
            for host in hostnames:
                response = await async_query_dns(loop, host, nameservers, timeout)
                results.append((response[0].host, nameservers))
        except Exception:
            pass

    if fallback_to_default and not results:
        try:
            response = await async_query_dns(loop, hostname, None, timeout)
            results.append((response[0].host, [None, ]))
        except Exception:
            pass

    if callback:
        # call callback function and handle async callback functions
        callback_function = callback(loop, hostname, results)
        if isawaitable(callback_function):
            await callback(loop, hostname, results)
    return results


def async_query_dns_list(names_to_query: List[dict], timeout: float,
                         greedy=False, fallback_to_default=True, callback=None) -> Tuple[str, list]:
    """
    DNS query a list of hostnames
    :param fallback_to_default: fallback to default dns server in case of dns failure
    :param names_to_query: list of hostnames dicts  to resolve (dict keys: [hostname : str, nameservers: list])
    :param timeout: request time per dns query
    :param greedy: if True - return the dns responses from all the given nameservers.
                    otherwise return only the response from the first dns server that resolves this hostname.
    :param callback: callback to call after the dns query
            callback signature: callback(loop: asyncio.AbstractEventLoop, hostname: str, results: list)
    :return: tuple of dns results tuple -> (resolved_ip, resolving_nameserver)
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    tasks = [query_dns_servers(loop, host.get('hostname'), host.get('nameservers'),
                               timeout, greedy, fallback_to_default=fallback_to_default, callback=callback)
             for host in names_to_query if host.get('hostname')]
    responses = loop.run_until_complete(asyncio.gather(*tasks))
    return responses


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
