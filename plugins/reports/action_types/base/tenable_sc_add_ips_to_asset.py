import logging

from axonius.types.enforcement_classes import EntitiesResult
from axonius.plugin_base import PluginBase
from axonius.clients.tenable_sc.connection import \
    TenableSecurityScannerConnection
from reports.action_types.action_type_base import ActionTypeBase, generic_fail
from reports.action_types.base.ips_scans_utils import get_ips_from_view

logger = logging.getLogger(f'axonius.{__name__}')


class TenableScAddIPsToAsset(ActionTypeBase):
    '''
    Add ips to assets at Tenable SC
    '''

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use Tenable SC Adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'Tenable SC Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
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
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'asset_name',
                    'title': 'Asset Name',
                    'type': 'string'
                },
                {
                    'name': 'create_new_asset',
                    'title': 'Create New Asset',
                    'type': 'bool'
                },
                {
                    'name': 'use_public_ips',
                    'title': 'Use Public IPS',
                    'type': 'bool'},
                {
                    'name': 'use_private_ips',
                    'title': 'Use Private IPS',
                    'type': 'bool'
                }
            ],
            'required': [
                'asset_name',
                'create_new_asset',
                'use_private_ips',
                'use_public_ips',
                'use_adapter'

            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'asset_name': None,
            'create_new_asset': False,
            'use_private_ips': True,
            'use_public_ips': True,
            'use_adapter': True,
            'verify_ssl': False,
            'domain': None,
            'https_proxy': None,
            'username': None,
            'password': None
        }

    # pylint: disable=R0912,R0914,R0915,R1702
    def _run(self) -> EntitiesResult:
        current_result = self._get_entities_from_view({
            'adapters.data.network_interfaces.ips': 1,
            'internal_axon_id': 1
        })
        ips, results = get_ips_from_view(current_result,
                                         self._config['use_public_ips'],
                                         self._config['use_private_ips'])
        asset_name = self._config['asset_name']
        create_new_asset = self._config['create_new_asset']
        action_name = 'create_asset_with_ips' if create_new_asset else 'add_ips_to_asset'
        tenable_sc_dict = {'ips': list(ips), 'asset_name': asset_name}
        if self._config['use_adapter'] is True:
            response = PluginBase.Instance.request_remote_plugin(action_name, 'tenable_security_center_adapter',
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
