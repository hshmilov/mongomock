import logging

from axonius.clients.tenable_io.connection import TenableIoConnection
from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.action_type_base import (ActionTypeBase,
                                                   add_node_selection,
                                                   generic_fail, add_node_default)
from reports.action_types.base.ips_scans_utils import get_ips_from_view

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'tenable_io_adapter'


class TenableIoAddIPsToScan(ActionTypeBase):
    '''
    Add IPs to scan at tenable IO
    '''

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the Tenable.io adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'Tenable.io domain',
                    'type': 'string'
                },
                {
                    'name': 'access_key',
                    'title': 'Access API key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'secret_key',
                    'title': 'Secret API key',
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
                    'title': 'HTTPS proxy',
                    'type': 'string'
                },
                {
                    'name': 'scan_name',
                    'title': 'Scan name',
                    'type': 'string'
                },
                {
                    'name': 'use_public_ips',
                    'title': 'Use public IP addresses',
                    'type': 'bool'},
                {
                    'name': 'use_private_ips',
                    'title': 'Use private IP addresses',
                    'type': 'bool'
                },
                {
                    'name': 'exclude_ipv6',
                    'title': 'Exclude IPv6 addresses',
                    'type': 'bool'
                },
                {
                    'name': 'cidr_exclude_list',
                    'type': 'string',
                    'title': 'CIDRs exclude list'
                }
            ],
            'required': [
                'verify_ssl',
                'scan_name',
                'use_private_ips',
                'use_public_ips',
                'use_adapter',
                'exclude_ipv6'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'scan_name': None,
            'cidr_exclude_list': None,
            'exclude_ipv6': False,
            'use_private_ips': True,
            'use_public_ips': True,
            'access_key': None,
            'secret_key': None,
            'use_adapter': True,
            'verify_ssl': False,
            'domain': None,
            'https_proxy': None,
        })

    # pylint: disable=R0912,R0914,R0915,R1702,W0212
    def _run(self) -> EntitiesResult:
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        current_result = self._get_entities_from_view({
            'adapters.data.network_interfaces.ips': 1,
            'internal_axon_id': 1
        })
        ips, results = get_ips_from_view(current_result,
                                         self._config['use_public_ips'],
                                         self._config['use_private_ips'],
                                         self._config.get('exclude_ipv6') or False,
                                         cidr_exclude_list=self._config.get('cidr_exclude_list'))
        scan_name = self._config['scan_name']
        action_name = 'add_ips_to_scans'
        tenable_io_dict = {'ips': list(ips), 'scan_name': scan_name}
        if self._config['use_adapter'] is True:
            response = self._plugin_base.request_remote_plugin(action_name, adapter_unique_name,
                                                               'post', json=tenable_io_dict)
            if response.status_code == 200:
                return results
            if response.status_code == 500:
                return generic_fail(self._internal_axon_ids, reason=response.data.message)
            return generic_fail(self._internal_axon_ids)
        try:
            if not self._config.get('domain') or not self._config.get('access_key')\
                    or not self._config.get('secret_key'):
                return generic_fail(self._internal_axon_ids, reason='Missing Parameters For Connection')
            connection = TenableIoConnection(domain=self._config['domain'],
                                             verify_ssl=self._config['verify_ssl'],
                                             access_key=self._config.get('access_key'),
                                             secret_key=self._config.get('secret_key'),
                                             https_proxy=self._config.get('https_proxy'))
            with connection:
                connection.add_ips_to_scans(tenable_io_dict)
                return results
        except Exception as e:
            logger.exception(f'Got exception creating Tenable asset')
            return generic_fail(self._internal_axon_ids, reason=f'Got exception creating TenableIO '
                                                                f'target group computer: {str(e)}')
