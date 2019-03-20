import logging

from axonius.types.enforcement_classes import EntitiesResult
from axonius.plugin_base import PluginBase
from axonius.clients.tenable_io.connection import TenableIoConnection
from reports.action_types.action_type_base import ActionTypeBase, generic_fail
from reports.action_types.base.ips_scans_utils import get_ips_from_view

logger = logging.getLogger(f'axonius.{__name__}')


class TenableIoAddIPsToTargetGroup(ActionTypeBase):
    '''
    Add IPs to target lists at tenable IO
    '''

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use ServiceNow Adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'TenableIO Domain',
                    'type': 'string'
                },
                {
                    'name': 'access_key',
                    'title': 'Access API Key (instead of user/password)',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'secret_key',
                    'title': 'Secret API key (instead of user/password)',
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
                    'name': 'target_group_name',
                    'title': 'Target Group Name',
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
                'target_group_name',
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
            'target_group_name': None,
            'create_new_asset': False,
            'use_private_ips': True,
            'use_public_ips': True,
            'access_key': None,
            'secret_key': None,
            'use_adapter': True,
            'verify_ssl': False,
            'domain': None,
            'https_proxy': None,
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
        target_group_name = self._config['target_group_name']
        create_new_asset = self._config['create_new_asset']
        action_name = 'create_target_group_with_ips' if create_new_asset else 'add_ips_to_target_group'
        tenable_io_dict = {'ips': list(ips), 'target_group_name': target_group_name}
        if self._config['use_adapter'] is True:
            response = PluginBase.Instance.request_remote_plugin(action_name, 'tenable_io_adapter',
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
                if create_new_asset:
                    connection.create_target_group_with_ips(tenable_io_dict)
                else:
                    connection.add_ips_to_target_group(tenable_io_dict)
                return results
        except Exception as e:
            logger.exception(f'Got exception creating Tenable asset')
            return generic_fail(self._internal_axon_ids, reason=f'Got exception creating TenableIO '
                                                                f'target group computer: {str(e)}')
