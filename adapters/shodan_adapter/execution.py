import logging
import ipaddress
import re

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.mixins.triggerable import RunIdentifier, Triggerable
from axonius.plugin_base import EntityType
from axonius.types.correlation import CorrelationReason, CorrelationResult
from axonius.utils.gui_helpers import find_entity_field
from axonius.utils.datetime import parse_date
from axonius.clients.shodan.connection import ShodanConnection
from axonius.devices.device_adapter import ShodanVuln
from axonius.devices.device_adapter import DeviceAdapterSoftwareCVE
logger = logging.getLogger(f'axonius.{__name__}')

INVALID_HOSTS = ['localhost', 'ubuntu']
IP_REGEX = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'

# pylint: disable=too-many-branches


def get_entity_field_list(device_data, field):
    """" find_entity_field returns object when single
         field exist and list when multiple objects exist.
         it hard to work like this, so this wrapper always returns a list """

    result = find_entity_field(device_data, field)
    if result is None:
        return []
    if not isinstance(result, list):
        result = [result]
    return result


class ShodanExecutionMixIn(Triggerable):
    @staticmethod
    def get_valid_config(config):
        try:
            required_args = ['apikey']
            if not all(arg in config for arg in required_args):
                return None
        except Exception:
            logger.exception('Error when preparing arguments')
            return None
        return config

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name != 'enrich':
            return super()._triggered(job_name, post_json, run_identifier, *args)

        logger.info('Shodan was Triggered.')
        internal_axon_ids = post_json['internal_axon_ids']
        client_config = post_json['client_config']

        client_config = self.get_valid_config(client_config)
        if not client_config:
            logger.debug(f'Bad config {client_config}')
            return {'status': 'error', 'message': f'Argument Error: Please specify a valid apikey'}

        with ShodanConnection(apikey=client_config['apikey'],
                              domain_prefered=client_config.get('domain'),
                              https_proxy=client_config.get('https_proxy')) as connection:
            results = {}
            for id_ in internal_axon_ids:
                device = list(self.devices.get(internal_axon_id=id_))[0]
                internal_axon_id, result = self._handle_device(device, connection)
                results[internal_axon_id] = result
        logger.info('Shodan Trigger end.')
        return results

    @staticmethod
    def _get_enrichment_ips(device):
        """ find all ips to use for the device enrichment """

        ips = get_entity_field_list(device.data, 'specific_data.data.network_interfaces.ips')
        ips = filter(lambda ip: re.match(IP_REGEX, ip), ips)
        ips = list(filter(lambda ip: not ipaddress.ip_address(ip).is_private, ips))

        return ips

    @staticmethod
    def _get_enrichment_client_id(id_, ip):
        return '_'.join(('shodanenrichment', id_, ip))

    @staticmethod
    def _parse_shodan_data(shodan_info):
        try:
            shodan_info_data = shodan_info.get('data')
            if isinstance(shodan_info_data, dict):
                shodan_info_data = [shodan_info_data]
            if not isinstance(shodan_info_data, list):
                shodan_info_data = []
            vulns_dict_list = []
            software_cves = []
            if isinstance(shodan_info_data, list):
                vulns_dict_list = [shodan_info_data_item.get('vulns')
                                   for shodan_info_data_item in shodan_info_data
                                   if isinstance(shodan_info_data_item.get('vulns'), dict)]
            vulns = []
            for vulns_dict in vulns_dict_list:
                for vuln_name, vuln_data in vulns_dict.items():
                    try:
                        vulns.append(ShodanVuln(summary=vuln_data.get('summary'),
                                                vuln_name=vuln_name,
                                                cvss=float(vuln_data.get('cvss'))
                                                if vuln_data.get('cvss') is not None
                                                else None))
                        software_cves.append(DeviceAdapterSoftwareCVE(cve_id=vuln_name))
                    except Exception:
                        logger.exception(f'Problem adding vuln name {vuln_name}')
            cpe = []
            http_server = None
            http_site_map = None
            http_location = None
            http_security_text_hash = None
            for shoda_data_raw in shodan_info_data:
                try:
                    if shoda_data_raw.get('cpe'):
                        cpe.extend(shoda_data_raw.get('cpe'))
                    http_info = shoda_data_raw.get('http')
                    if http_info and isinstance(http_info, dict):
                        if not http_server:
                            http_server = http_info.get('server')
                        if not http_site_map:
                            http_site_map = http_info.get('sitemap')
                        if not http_location:
                            http_location = http_info.get('location')
                        if not http_security_text_hash:
                            http_security_text_hash = http_info.get('securitytxt_hash')
                except Exception:
                    logger.exception(f'problem with shodan data raw {shoda_data_raw}')
            if not cpe:
                cpe = None
            return {'city': shodan_info.get('city'),
                    'region_code': shodan_info.get('region_code'),
                    'country_name': shodan_info.get('country_name'),
                    'org': shodan_info.get('org'),
                    'os': shodan_info.get('os'),
                    'cpe': cpe,
                    'isp': shodan_info.get('isp'),
                    'ports': shodan_info.get('ports') if isinstance(shodan_info.get('ports'), list) else None,
                    'vulns': vulns,
                    'http_location': http_location,
                    'http_server': http_server,
                    'http_site_map': http_site_map,
                    'http_security_text_hash': http_security_text_hash,
                    'software_cves': software_cves}
        except Exception:
            logger.exception(f'Problem parsing shodan info')
        return None

    def _handle_ip(self, device, ip, connection):
        try:
            client_id = self._get_enrichment_client_id(device.internal_axon_id, ip)
            result = connection.get_ip_info2(ip)
            if 'error' in result:
                logger.info(f'error for fetching ip {ip}: error {result["error"]}')
                return False

            data = self._parse_shodan_data(result)
            if not data:
                return False
            new_device = self._new_device_adapter()
            new_device.id = client_id
            new_device.add_public_ip(ip)
            hostnames = result.get('hostnames')
            if hostnames and isinstance(hostnames, list):
                new_device.hostname = hostnames[0]
            last_update = result.get('last_update')
            if last_update:
                new_device.last_seen = parse_date(last_update)
            new_device.add_nic(None, [ip])
            new_device.set_shodan_data(**data)
            new_device.set_raw(result)
            for data_item in result.get('data') or []:
                try:
                    new_device.add_open_port(port_id=data_item.get('port'),
                                             protocol=data_item.get('transport'),
                                             service_name=(data_item.get('_shodan') or {}).get('module'))
                except Exception:
                    logger.exception(f'Failed to add open port')

            # Here we create a new device adapter tab out of cycle
            self._save_data_from_plugin(client_id,
                                        {'raw': [], 'parsed': [new_device.to_dict()]},
                                        EntityType.Devices,
                                        False)

            self._save_field_names_to_db(EntityType.Devices)
            self._correlate_enrichment_if_needed(device, new_device)
            return True
        except Exception as e:
            logger.exception(f'Failed to fetch ip info for {ip}')
            return False

    def _handle_device(self, device, connection):
        try:
            if not device.specific_data:
                json = {'success': False, 'value': 'Shodan Error: Adapters not found'}
                return (device.internal_axon_id, json)

            ips = self._get_enrichment_ips(device)
            if not ips:
                json = {'success': False, 'value': 'Shodan Error: Missing Public IPs'}
                return (device.internal_axon_id, json)

            if not any([self._handle_ip(device, ip, connection) for ip in ips]):
                return (device.internal_axon_id, {'success': False, 'value': 'Shodan Enrichment - no results'})

            return (device.internal_axon_id, {'success': True, 'value': 'Shodan Enrichment success'})
        except Exception as e:
            logger.exception('Exception while handling devices')
            return (device.internal_axon_id, {'success': False, 'value': f'Shodan Enrichment Error: {str(e)}'})

    def _correlate_enrichment_if_needed(self, device, new_device):
        try:
            id_ = get_entity_field_list(device.data, 'adapters_data.shodan_adapter.id')
            id_ = ''.join(id_)

            # If id is in the "old" device id so this devices are already correlated
            # no need to correlate again.
            if new_device['id'] in id_:
                return

            logger.debug('Correlating enrichment')
            first_plugin_unique_name = device.specific_data[0][PLUGIN_UNIQUE_NAME]
            first_device_adapter_id = device.specific_data[0]['data']['id']
            new_device_id = new_device.id
            new_device = new_device.to_dict()

            associated_adapters = [(first_plugin_unique_name, first_device_adapter_id),
                                   (self.plugin_unique_name, new_device_id)]

            correlation = CorrelationResult(associated_adapters=associated_adapters,
                                            data={'reason': 'Shodan Enrichment'},
                                            reason=CorrelationReason.ShodanEnrichment)

            self.link_adapters(EntityType.Devices, correlation)
        except Exception as e:
            logger.exception('Failed to correlate')
