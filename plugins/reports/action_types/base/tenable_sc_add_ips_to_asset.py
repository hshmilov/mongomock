import logging

from axonius.types.enforcement_classes import EntitiesResult
from axonius.clients.tenable_sc.connection import \
    TenableSecurityScannerConnection
from reports.action_types.action_type_base import ActionTypeBase, generic_fail, add_node_selection, add_node_default
from reports.action_types.base.ips_scans_utils import get_ips_from_view

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'tenable_security_center_adapter'


class TenableScAddIPsToAsset(ActionTypeBase):
    '''
    Add ips to assets at Tenable SC
    '''

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the Tenable.sc Adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'Tenable.sc domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
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
                    'name': 'asset_name',
                    'title': 'Asset name',
                    'type': 'string'
                },
                {
                    'name': 'create_new_asset',
                    'title': 'Create new asset',
                    'type': 'bool'
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
                    'name': 'override_ips',
                    'title': 'Override current IP address list',
                    'type': 'bool',
                },
                {
                    'name': 'cidr_exclude_list',
                    'type': 'string',
                    'title': 'CIDRs exclude list'
                }
            ],
            'required': [
                'verify_ssl',
                'asset_name',
                'create_new_asset',
                'use_private_ips',
                'use_public_ips',
                'use_adapter',
                'override_ips',
                'exclude_ipv6'

            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'asset_name': None,
            'create_new_asset': False,
            'use_private_ips': True,
            'cidr_exclude_list': None,
            'use_public_ips': True,
            'use_adapter': True,
            'verify_ssl': False,
            'exclude_ipv6': False,
            'domain': None,
            'https_proxy': None,
            'username': None,
            'password': None,
            'override_ips': False
        })

    # pylint: disable=R0912,R0914,R0915,R1702,W0212
    def _run(self) -> EntitiesResult:
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(
            ADAPTER_NAME, self.action_node_id)
        current_result = self._get_entities_from_view({
            'adapters.data.network_interfaces.ips': 1,
            'internal_axon_id': 1
        })
        ips, results = get_ips_from_view(current_result,
                                         self._config['use_public_ips'],
                                         self._config['use_private_ips'],
                                         self._config.get('exclude_ipv6') or False,
                                         cidr_exclude_list=self._config.get('cidr_exclude_list'))
        asset_name = self._config['asset_name']
        create_new_asset = self._config['create_new_asset']
        override = self._config.get('override_ips') or False
        action_name = 'create_asset_with_ips' if create_new_asset else 'add_ips_to_asset'
        tenable_sc_dict = {'ips': list(ips), 'asset_name': asset_name, override: override}
        if self._config['use_adapter'] is True:
            response = self._plugin_base.request_remote_plugin(action_name, adapter_unique_name,
                                                               'post', json=tenable_sc_dict)
            if response.status_code == 200:
                return results
            if response.status_code == 500:
                return generic_fail(self._internal_axon_ids, reason=response.data.message)
            return generic_fail(self._internal_axon_ids)
        try:
            verify_ssl = False
            if 'verify_ssl' in self._config:
                verify_ssl = bool(self._config['verify_ssl'])
            if not self._config.get('domain') or not self._config.get('username') or not self._config.get('password'):
                return generic_fail(self._internal_axon_ids, reason='Missing Parameters For Connection')
            connection = TenableSecurityScannerConnection(
                domain=self._config['domain'],
                username=self._config['username'], password=self._config['password'],
                verify_ssl=verify_ssl)
            with connection:
                if create_new_asset:
                    connection.create_asset_with_ips(tenable_sc_dict)
                else:
                    connection.add_ips_to_asset(tenable_sc_dict)
                return results
        except Exception as e:
            logger.exception(f'Got exception creating Tenable asset')
            return generic_fail(self._internal_axon_ids, reason=f'Got exception creating TenableSC '
                                                                f'asset computer: {str(e)}')
