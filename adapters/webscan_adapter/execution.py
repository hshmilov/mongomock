import logging
import ipaddress

from typing import List, Tuple

from dataclasses import dataclass

from axonius.entities import EntityType
from axonius.mixins.triggerable import RunIdentifier, Triggerable
from axonius.utils.db_querying_helper import iterate_axonius_entities
from axonius.utils.dns import query_dns
from axonius.blacklists import DANGEROUS_IPS
from webscan_adapter.connection import WebscanConnection
from webscan_adapter.scanners.cert_scanner import CertScanner

logger = logging.getLogger(f'axonius.{__name__}')


@dataclass
class AdapterScanHostnames:
    meta: dict
    hostname: str
    ips: List[str]


class WebscanExecutionMixIn(Triggerable):
    '''
    This class should handle webscan enrichment action
    Notes:
        The problem we have is that we can get an ip of a server that configured with vhosts
        The problem is if we dont request the server by domain name we will not get any data.
        One solution for this is to get the server common name/names from its SSL Certificate
        and use it as the server domain
    '''

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name != 'enrich':
            return super()._triggered(job_name, post_json, run_identifier, *args)

        logger.info('Webscan was Triggered.')
        internal_axon_ids = post_json['internal_axon_ids']
        client_config = post_json['client_config']

        if not client_config:
            logger.exception(f'Bad config')
            return {
                'status': 'error',
                'message': f'Argument Error: Bad Config'
            }
        results = dict()
        # Get devices details
        devices = iterate_axonius_entities(EntityType.Devices, internal_axon_ids)
        for device in devices:
            _id = None
            try:
                _id = device['internal_axon_id']
                result_value = self._handle_device(device)
                results[_id] = result_value
            except Exception as e:
                logger.exception(f'Failed to handle internal axon id {_id}')
                results[_id] = {
                    'success': False,
                    'value': str(e)
                }
        logger.info('Webscan Trigger end.')
        return results

    @staticmethod
    def _get_scan_hostnames(device: dict) -> List[AdapterScanHostnames]:
        """
        find all hostnames / ips to use for the device action
        :param device: device data
        :return: list of : AdapterScanHostnames for all adapters
        """
        result = []
        adapters = device.get('adapters')
        if not adapters:
            return result
        # Sort adapters data by the most recent one.
        adapters.sort(key=lambda i: i['accurate_for_datetime'], reverse=True)
        for adapter in adapters:
            try:
                adapter_ips = []
                adapter_data = adapter['data']
                adapter_hostname = adapter_data.get('hostname')
                for interface in adapter_data.get('network_interfaces'):
                    if not interface:
                        continue
                    ips = interface.get('ips')
                    if ips:
                        adapter_ips.extend(x for x in ips
                                           if isinstance(ipaddress.ip_address(x), ipaddress.IPv4Address) and
                                           not ipaddress.ip_address(x).is_loopback and x not in DANGEROUS_IPS)
                adapter_meta = adapter.copy()
                adapter_meta.pop('data')
                adapter_meta['adapter_unique_id'] = adapter.get('data', {}).get('id')
                result.append(AdapterScanHostnames(meta=adapter_meta, hostname=adapter_hostname, ips=adapter_ips))
            except Exception:
                logger.exception('Error getting network interfaces')

        return result

    def _handle_domain(self, adapter_meta: dict, hostname: str):
        """
        Get a domain and the meta data of the device and fetch its data using webscan adapter
        :param adapter_meta: adapter meta (for tagging the results)
        :param hostname: hostname to scan
        :return:
        """
        logger.debug(f'Scanning {hostname}')
        # create a new connection
        connection = WebscanConnection(domain=hostname)
        data = connection.get_device_list()
        new_device = list(self._parse_raw_data(data))[0]
        new_data = new_device.to_dict()
        # add the new device data as a tag
        self.devices.add_adapterdata(
            [(adapter_meta['plugin_unique_name'], adapter_meta['adapter_unique_id'])], new_data,
            action_if_exists='update',  # If the tag exists, we update it using deep merge (and not replace it).
            client_used=adapter_meta['client_used']
        )
        self._save_field_names_to_db(EntityType.Devices)
        return hostname

    @staticmethod
    def get_common_name_from_ip(ip, query_timeout=5) -> str:
        """
        Getting ssl common names from the given ip
        :param ip: if to get its cert common names
        :param query_timeout: validate dns query timeout
        :return: domain
        Notes:
            Sometimes the common names are related to other servers,
            So the best think to do is to validate the ip via dns query
        """
        common_names = CertScanner.get_cert_info(domain=ip).get('alt_name')
        if not common_names:
            return ''
        # common name should look like [['dns','*.google.com'],..] so we filter some values
        names = [name[1] for name in common_names if len(name) > 1 and '*' not in name]
        for name in names:
            # ip validation
            dns_response = query_dns(name, timeout=query_timeout)
            if dns_response == ip:
                return name
            logger.debug(f'{name} is not {ip}, query response: {dns_response}')
        return ''

    @staticmethod
    def get_reachable_hostname(adapters_hostnames: List[AdapterScanHostnames]) -> Tuple[dict, str]:
        """
        Getting the best reachable hostname from adapters data.
        :param adapters_hostnames:
        :return:
        """
        for data in adapters_hostnames:
            try:
                # we prefer hostname first
                if data.hostname and (WebscanConnection.test_reachability(data.hostname, ssl=True) or
                                      WebscanConnection.test_reachability(data.hostname, ssl=False)):
                    return data.meta, data.hostname
                # loop the adapter's IPs and find a reachable hostname
                for ip in data.ips:
                    try:
                        domain = WebscanExecutionMixIn.get_common_name_from_ip(ip)
                    except Exception:
                        logger.exception('Error getting common name')
                        continue
                    domain = domain or ip
                    if WebscanConnection.test_reachability(domain, ssl=True) or \
                            WebscanConnection.test_reachability(domain, ssl=False):
                        return data.meta, domain
            except Exception:
                logger.exception(f'Error getting reachable hostname from adapter')
        return {}, ''

    def _handle_device(self, device: dict) -> dict:
        '''
        Get an axon device, handle the required job and return its output
        :param device:
        :return:
        '''
        try:
            if not device.get('adapters'):
                json = {
                    'success': False,
                    'value': 'Webscan Error: Adapters not found'
                }
                return json
            adapters_hostnames = self._get_scan_hostnames(device)
            if not adapters_hostnames or not \
                    any(adapter_hostname.hostname or adapter_hostname.ips for adapter_hostname in adapters_hostnames):
                json = {
                    'success': False,
                    'value': f'Webscan Error: Missing Hostname and IPs'
                }
                return json

            reachable_hostname_adapter, reachable_hostname = self.get_reachable_hostname(adapters_hostnames)
            if not reachable_hostname:
                json = {
                    'success': False,
                    'value': 'Webscan Enrichment Error: No reachable Hostname or IP'
                }
                return json

            scanned_domain = self._handle_domain(reachable_hostname_adapter, reachable_hostname)

            json = {
                'success': True,
                'value': f'Webscan Enrichment success, scanned domain: {scanned_domain}'
            }
            return json

        except Exception as e:
            logger.exception('Exception while handling devices')
            return {
                'success': False,
                'value': f'Webscan Enrichment Error: {str(e)}'
            }
