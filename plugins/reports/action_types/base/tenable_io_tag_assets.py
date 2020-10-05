import logging

from axonius.clients.tenable_io.connection import TenableIoConnection
from axonius.types.enforcement_classes import EntitiesResult
from axonius.types.enforcement_classes import EntityResult
from reports.action_types.action_type_base import (ActionTypeBase,
                                                   add_node_selection,
                                                   generic_fail, add_node_default)

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'tenable_io_adapter'


class TenableIoTagAssets(ActionTypeBase):
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
                    'name': 'action',
                    'title': 'Action',
                    'type': 'string',
                    'enum': ['Add', 'Remove']
                },
                {
                    'name': 'tags_names',
                    'title': 'Tags names',
                    'type': 'string'
                }
            ],
            'required': [
                'verify_ssl',
                'tags_names',
                'action'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'tags_names': None,
            'action': 'Add',
            'access_key': None,
            'secret_key': None,
            'use_adapter': True,
            'verify_ssl': False,
            'domain': None,
            'https_proxy': None,
        })

    # pylint: disable=protected-access
    def _run(self) -> EntitiesResult:
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        current_result = self._get_entities_from_view({
            'adapters.data.asset_uuid': 1,
            'internal_axon_id': 1,
            'adapters.plugin_name': 1,
        })
        assets = []
        results = []
        # pylint: disable=R1702
        for entry in current_result:
            try:
                for adapter_data in entry['adapters']:
                    if adapter_data.get('plugin_name') != ADAPTER_NAME:
                        continue
                    device_id = adapter_data['data'].get('asset_uuid')
                    if not device_id:
                        continue
                    assets.append(device_id)
                results.append(EntityResult(entry['internal_axon_id'], True, 'success'))
            except Exception:
                logger.exception(f'Failed adding nic entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))

        tags_names = self._config['tags_names'].split(',')
        action_name = 'tag_assets'
        tenable_io_dict = {'action': self._config['action'].lower(), 'tags': tags_names, 'assets': assets}
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
                connection.tag_assets(tenable_io_dict)
                return results
        except Exception as e:
            logger.exception(f'Got exception creating Tenable asset')
            return generic_fail(self._internal_axon_ids, reason=f'Got exception creating TenableIO '
                                                                f'target group computer: {str(e)}')
