import logging

from axonius.clients.tenable_io.connection import TenableIoConnection
from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.action_type_base import (ActionTypeBase,
                                                   add_node_selection,
                                                   generic_fail, add_node_default)
from reports.action_types.base.ips_scans_utils import get_ips_from_view

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'tenable_io_adapter'


class TenableIoAddIPsToTargetGroup(ActionTypeBase):
    '''
    Add IPs to target lists at tenable IO
    '''

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
                {
                    'name': 'target_group_name',
                    'title': 'Target Group Name',
                    'type': 'string'
                },
                {
                    'name': 'create_new_asset',
                    'title': 'Create New Target Group',
                    'type': 'bool'
                },
                {
                    'name': 'use_public_ips',
                    'title': 'Use Public IPs',
                    'type': 'bool'},
                {
                    'name': 'use_private_ips',
                    'title': 'Use Private IPs',
                    'type': 'bool'
                },
                {
                    'name': 'exclude_ipv6',
                    'title': 'Exclude IPv6',
                    'type': 'bool'
                },
                {
                    'name': 'override_ips',
                    'title': 'Override Current IPs List',
                    'type': 'bool',
                },
            ],
            'required': [
                'target_group_name',
                'create_new_asset',
                'use_private_ips',
                'use_public_ips',
                'use_adapter',
                'exclude_ipv6',
                'override_ips'

            ],
            'type': 'array'
        }
        return add_node_selection(schema, ADAPTER_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'target_group_name': None,
            'create_new_asset': False,
            'exclude_ipv6': False,
            'use_private_ips': True,
            'use_public_ips': True,
            'access_key': None,
            'secret_key': None,
            'use_adapter': True,
            'verify_ssl': False,
            'domain': None,
            'https_proxy': None,
            'override_ips': False
        }, ADAPTER_NAME)

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
                                         self._config.get('exclude_ipv6') or False)
        target_group_name = self._config['target_group_name']
        create_new_asset = self._config['create_new_asset']
        override = self._config.get('override_ips') or False
        action_name = 'create_target_group_with_ips' if create_new_asset else 'add_ips_to_target_group'
        tenable_io_dict = {'ips': list(ips), 'target_group_name': target_group_name, 'override': override}
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
                if create_new_asset:
                    connection.create_target_group_with_ips(tenable_io_dict)
                else:
                    connection.add_ips_to_target_group(tenable_io_dict)
                return results
        except Exception as e:
            logger.exception(f'Got exception creating Tenable asset')
            return generic_fail(self._internal_axon_ids, reason=f'Got exception creating TenableIO '
                                                                f'target group computer: {str(e)}')
