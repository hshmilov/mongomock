import logging

from axonius.clients.tenable_io.connection import TenableIoConnection
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.utils.parsing import is_valid_ipv4, is_valid_ipv6
from reports.action_types.action_type_base import (ActionTypeBase,
                                                   add_node_selection,
                                                   generic_fail, add_node_default)

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'tenable_io_adapter'


class TenableIoCreateAsset(ActionTypeBase):
    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use Tenable.io Adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'Tenable.io Domain',
                    'type': 'string'
                },
                {
                    'name': 'access_key',
                    'title': 'Access API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'secret_key',
                    'title': 'Secret API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
            ],
            'required': [
                'verify_ssl',
                'use_adapter'
            ],
            'type': 'array'
        }
        return add_node_selection(schema, ADAPTER_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'access_key': None,
            'secret_key': None,
            'use_adapter': True,
            'verify_ssl': False,
            'domain': None,
            'https_proxy': None,
        }, ADAPTER_NAME)

    def _run(self) -> EntitiesResult:
        try:
            # pylint: disable=protected-access
            adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
            current_result = self._get_entities_from_view({
                'adapters.data.network_interfaces.ips': 1,
                'internal_axon_id': 1
            })
            results = []
            for entry in current_result:
                results.append(self._create_tenable_io_asset(adapter_unique_name=adapter_unique_name,
                                                             entry=entry))
            return results
        except Exception:
            logger.exception(f'Problem with action Tenable IO create asset')
            return generic_fail(self._internal_axon_ids)

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_tenable_io_asset(self, adapter_unique_name, entry):
        try:
            fqdn = []
            operating_system = None
            ipv4 = []
            ipv6 = []
            mac_address = []
            for from_adapter in entry['adapters']:
                data_from_adapter = from_adapter['data']
                if data_from_adapter.get('hostname'):
                    fqdn.append(data_from_adapter.get('hostname'))
                if operating_system is None:
                    operating_system = data_from_adapter.get('os', {}).get('type')
                nics = data_from_adapter.get('network_interfaces')
                if nics and isinstance(nics, list):
                    for nic in nics:
                        ips = nic.get('ips')
                        if isinstance(ips, list):
                            for ip in ips:
                                if is_valid_ipv4(ip):
                                    ipv4.append(ip)
                                elif is_valid_ipv6(ip):
                                    ipv6.append(ip)
                        mac = nic.get('mac')
                        if mac:
                            mac_address.append(mac)
            tenable_io_dict = {'fqdn': fqdn, 'ipv4': ipv4,
                               'ipv6': ipv6, 'mac_address': mac_address}
            if operating_system:
                tenable_io_dict['operating_system'] = operating_system
            if self._config['use_adapter'] is True:
                response = self._plugin_base.request_remote_plugin('create_asset', adapter_unique_name,
                                                                   'post', json=tenable_io_dict)
                if response.status_code == 200:
                    return EntityResult(entry['internal_axon_id'], True, 'success')
                if response.status_code == 500:
                    return EntityResult(entry['internal_axon_id'], False, response.data.message)
                return EntityResult(entry['internal_axon_id'], False, 'Unexpected Error')
            if not self._config.get('domain') or not self._config.get('access_key')\
                    or not self._config.get('secret_key'):
                return EntityResult(entry['internal_axon_id'], False, 'Missing Parameters For Connection')
            connection = TenableIoConnection(domain=self._config['domain'],
                                             verify_ssl=self._config['verify_ssl'],
                                             access_key=self._config.get('access_key'),
                                             secret_key=self._config.get('secret_key'),
                                             https_proxy=self._config.get('https_proxy'))
            with connection:
                connection.create_asset(tenable_io_dict)
            return EntityResult(entry['internal_axon_id'], True, 'success')
        except Exception as e:
            logger.exception(f'Got exception creating Tenable asset')
            return EntityResult(entry['internal_axon_id'], False, 'Unexpected Error')
