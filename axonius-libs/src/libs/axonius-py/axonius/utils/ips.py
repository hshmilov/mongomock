import asyncio
import logging
from typing import Iterator, List, Union

from dataclasses import dataclass
from funcy import chunks
from netaddr import AddrFormatError, IPNetwork
from axonius.utils.dns import async_query_dns_list

logger = logging.getLogger(f'axonius.{__name__}')

DEFAULT_RESOLVE_TIMEOUT = 5
DEFAULT_SCAN_TIMEOUT = 3
MAX_HOSTS_PER_SCAN = 200


@dataclass
class PortScanResults:
    """
    Class for portscan results data
    """
    ip: str
    # open ports for the ip
    open_ports: List[int]


@dataclass
class PortScanStatus:
    """
    Class that holds scan status for host
    """
    ip: str
    port: int
    is_open: bool


def parse_ips_list(ips: Union[Iterator, str], resolve: bool = False,
                   dns_servers: List[str] = None, resolve_timeout: float = DEFAULT_RESOLVE_TIMEOUT) -> Iterator[str]:
    """
    parse ips/cidr/hostnames list or string into separate ips
    :param resolve_timeout: timeout for dns resolving
    :param dns_servers: resolving dns server
    :param resolve: resolve domains
    :param ips: list of ips/cidr or comma separated string.
                input example: '192.168.1.1, 192.168.2.0/16, google.com, ..'
    :return: list of valid ips.
    """
    ips = ips.split(',') if isinstance(ips, str) else ips
    not_ips = []
    for cidr in ips:
        cidr = cidr.strip()
        try:
            for ip in IPNetwork(cidr):
                yield str(ip)
        except AddrFormatError:
            not_ips.append(cidr)
        except Exception:
            logger.exception(f'Cannot parse {cidr}')
    # if there's an ip parse error we assume not_ips are hostnames and try to resolve them
    if resolve and not_ips:
        try:
            queries = [{
                'hostname': x,
                'nameservers': dns_servers
            } for x in not_ips]
            resolved = async_query_dns_list(queries, resolve_timeout)
            for query, response in zip(queries, resolved):
                try:
                    if response and response[0]:
                        # yield the resolved ip
                        yield response[0][0]
                    else:
                        logger.error(f'Cannot resolve {query.get("hostname")}')
                except Exception:
                    logger.exception(f'Cannot resolve query response. query: {query}')
        except Exception:
            logger.exception('Cannot resolve hostnames')


async def async_check_port(ip: str, port: int, loop: asyncio.AbstractEventLoop, timeout: float) \
        -> PortScanStatus:
    """
    check for open port
    :param ip: ip to be scanned
    :param port: port to be checked
    :param loop: asyncio eventloop
    :param timeout: port check timeout
    :return: ip, port, port_status.
    """
    try:
        conn = asyncio.open_connection(ip, port, loop=loop)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
        return PortScanStatus(ip=ip, port=port, is_open=True)
    except Exception:
        return PortScanStatus(ip=ip, port=port, is_open=False)


async def async_check_ports(ip: str, ports: List[int], loop: asyncio.AbstractEventLoop, timeout: float) \
        -> PortScanResults:
    """
    check for open ports
    :param ip: ip to be scanned
    :param ports: ports to scan
    :param loop: asyncio eventloop
    :param timeout: port check timeout
    :return: ip, list of open ports
    """
    tasks = [async_check_port(ip, port, loop, timeout) for port in ports]
    results = await asyncio.gather(*tasks)

    return PortScanResults(ip=ip, open_ports=[x.port for x in results if x and x.is_open])


def port_scan(hostnames, ports, timeout=DEFAULT_SCAN_TIMEOUT, dns_servers=None) -> Iterator[PortScanResults]:
    """
    async port scan
    :param hostnames: ips/hostnames to be scabbed
    :param ports: ports to scan
    :param timeout: check timeout (for each port)
    :param dns_server: dns server address for resolving the hostname (in addition to the default one)
    :return: list of ips and their open ports
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    for chunk in chunks(MAX_HOSTS_PER_SCAN, hostnames):
        try:
            parsed_ips = parse_ips_list(chunk, dns_servers=dns_servers, resolve=True)
            tasks = [asyncio.ensure_future(async_check_ports(d, ports, loop, timeout)) for d in parsed_ips]
            results = loop.run_until_complete(asyncio.gather(*tasks))
            yield from results
        except Exception:
            logger.exception('Port scan error')
