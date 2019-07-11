import logging
import ipaddress

from axonius.clients.censys.consts import (DOMAIN, IS_PAID_TIER, API_ID, API_SECRET, ACTION_SCHEMA)
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.mixins.triggerable import RunIdentifier, Triggerable
from axonius.plugin_base import EntityType
from axonius.types.correlation import CorrelationReason, CorrelationResult
from axonius.utils.gui_helpers import find_entity_field
from axonius.clients.censys.connection import CensysConnection

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=protected-access


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


class CensysExecutionMixIn(Triggerable):
    def get_valid_config(self, config):
        try:
            required_args = ACTION_SCHEMA['required']
            config = self._prepare_client_config(config)
            if not all(arg in config for arg in required_args):
                return None
        except Exception:
            logger.exception('Error when preparing arguments')
            return None
        return config

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name != 'execute':
            return super()._triggered(job_name, post_json, run_identifier, *args)

        logger.info('Censys was Triggered.')
        internal_axon_ids = post_json['internal_axon_ids']
        client_config = post_json['client_config']

        client_config = self.get_valid_config(client_config)
        if not client_config:
            logger.debug(f'Bad config {client_config}')
            return {'status': 'error', 'message': f'Argument Error: Please specify a valid api_id and api_secret'}

        devices = (list(result)[0] for result in (self.devices.get(internal_axon_id=id_) for id_ in internal_axon_ids))
        with CensysConnection(username=client_config[API_ID],
                              password=client_config[API_SECRET],
                              domain_preferred=client_config.get(DOMAIN),
                              free_tier=not client_config.get(IS_PAID_TIER),
                              https_proxy=client_config.get('https_proxy')) as connection:
            results = dict(self._handle_device(device, connection) for device in devices)
        logger.info('Censys Trigger end.')
        return results

    @staticmethod
    def _get_enrichment_hostnames(device):
        """ find all hostnames to use for the Censys enrichment """
        hostnames = get_entity_field_list(device.data, 'specific_data.data.hostname')
        hostnames = list(filter(None, filter(lambda name: name not in ['ubuntu', 'localhost'], hostnames)))
        return hostnames

    @staticmethod
    def _get_enrichment_ips(device):
        """ find all ips to use for the Censys enrichment """
        ips = get_entity_field_list(device.data, 'specific_data.data.network_interfaces.ips')
        ips = filter(None, filter(lambda ip: isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)
                                  and not ipaddress.ip_address(ip).is_private
                                  and not ipaddress.ip_address(ip).is_loopback, ips))
        return ips

    @staticmethod
    def _get_enrichment_client_id(id_, ip):
        return '_'.join(('censysenrichment', id_, ip))

    def _handle_ip(self, device, ip, connection):
        try:
            connection.search_type = 'ipv4'
            client_id = self._get_enrichment_client_id(device.internal_axon_id, ip)
            result = connection._get_view_details(ip)
            if 'error' in result:
                logger.info(f'error for fetching ip {ip}: error {result["error"]}')
                return False

            new_device = self._create_device(result)

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

    def _handle_hostname(self, device, hostname, connection):
        try:
            connection.search_type = 'websites'
            client_id = self._get_enrichment_client_id(device.internal_axon_id, hostname)
            result = connection._get_view_details(hostname)
            if 'error' in result:
                logger.info(f'error for fetching hostname {hostname}: error {result["error"]}')
                return False

            new_device = self._create_device(result)

            # Here we create a new device adapter tab out of cycle
            self._save_data_from_plugin(client_id,
                                        {'raw': [], 'parsed': [new_device.to_dict()]},
                                        EntityType.Devices,
                                        False)

            self._save_field_names_to_db(EntityType.Devices)
            self._correlate_enrichment_if_needed(device, new_device)
            return True

        except Exception as e:
            logger.exception(f'Failed to fetch hostname info for {hostname}')
            return False

    def _handle_device(self, device, connection):
        try:
            if not device.specific_data:
                json = {'success': False, 'value': 'Censys Error: Adapters not found'}
                return (device.internal_axon_id, json)

            ips = self._get_enrichment_ips(device)
            hostnames = self._get_enrichment_hostnames(device)

            # if there are no IPs or hostnames to look up, fail
            if not ips and not hostnames:
                json = {'success': False, 'value': 'Censys Error: Missing Public IPs or hostnames'}
                return (device.internal_axon_id, json)

            # if there are no results when looking up IPs or hostnames, fail
            if not any([self._handle_ip(device, ip, connection) for ip in ips]) \
                    and not any([self._handle_hostname(device, hostname, connection) for hostname in hostnames]):
                return (device.internal_axon_id, {'success': False, 'value': 'Censys Enrichment - no results'})

            return (device.internal_axon_id, {'success': True, 'value': 'Censys Enrichment success'})

        except Exception as e:
            logger.exception('Exception while handling devices')
            return (device.internal_axon_id, {'success': False, 'value': f'Censys Enrichment Error: {str(e)}'})

    def _correlate_enrichment_if_needed(self, device, new_device):
        try:
            id_ = get_entity_field_list(device.data, 'adapters_data.censys_adapter.id')
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
                                            data={'reason': 'Censys Enrichment'},
                                            reason=CorrelationReason.CensysEnrichment)

            self.link_adapters(EntityType.Devices, correlation)
        except Exception as e:
            logger.exception('Failed to correlate')
