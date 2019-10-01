import ipaddress
import logging

from axonius.utils.parsing import is_valid_ipv6
from axonius.types.enforcement_classes import EntityResult

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-branches
def get_ips_from_view(current_result, fetch_public_ips, fetch_private_ips, exclude_ipv6=False, cidr_exclude_list=None):
    if cidr_exclude_list and isinstance(cidr_exclude_list, str):
        cidr_exclude_list = cidr_exclude_list.split(',')
    else:
        cidr_exclude_list = []
    ips = set()
    results = []
    # pylint: disable=R1702
    for entry in current_result:
        try:
            for adapter_data in entry['adapters']:
                adapter_data = adapter_data.get('data') or {}
                if isinstance(adapter_data.get('network_interfaces'), list):
                    for nic in adapter_data.get('network_interfaces'):
                        if isinstance(nic.get('ips'), list):
                            for ip in nic.get('ips'):
                                got_exclude_cidr = False
                                for cidr_block in cidr_exclude_list:
                                    try:
                                        if ipaddress.ip_address(ip) in ipaddress.ip_network(cidr_block):
                                            got_exclude_cidr = True
                                    except Exception:
                                        pass
                                if got_exclude_cidr:
                                    continue
                                if exclude_ipv6 and is_valid_ipv6(ip):
                                    continue
                                is_private = ipaddress.ip_address(ip).is_private
                                if fetch_private_ips and is_private:
                                    ips.add(ip)
                                elif fetch_public_ips and not is_private:
                                    ips.add(ip)
            results.append(EntityResult(entry['internal_axon_id'], True, 'success'))
        except Exception:
            logger.exception(f'Failed adding nic entry {entry}')
            results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
    return ips, results
