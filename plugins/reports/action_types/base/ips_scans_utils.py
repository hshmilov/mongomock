import ipaddress
import logging

from axonius.types.enforcement_classes import EntityResult

logger = logging.getLogger(f'axonius.{__name__}')


def get_ips_from_view(current_result, fetch_public_ips, fetch_private_ips):
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
                                is_private = ipaddress.ip_address(ip).is_private
                                if fetch_private_ips and is_private:
                                    ips.add(ip)
                                elif fetch_public_ips and not is_private:
                                    ips.add(ip)
            results.append(EntityResult(entry['internal_axon_id'], True, 'sucesss'))
        except Exception:
            logger.exception(f'Failed adding nic entry {entry}')
            results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
    return ips, results
