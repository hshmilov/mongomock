import logging

from funcy import chunks

from axonius.consts.plugin_consts import WEBSCAN_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.plugin_base import PluginBase
from reports.action_types.action_type_base import ActionTypeBase, generic_fail, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

CHUNK_SIZE = 10000
# pylint: disable=protected-access
DEFAULT_SSL_PORT = 443
DEFAULT_POOL_SIZE = 10


class WebscanEnrichment(ActionTypeBase):
    @staticmethod
    def prettify_output(id_, result: dict) -> EntityResult:
        value = result['value']
        success = result['success']
        return EntityResult(id_, success, value)

    @staticmethod
    def config_schema() -> dict:
        action_schema = {
            'items': [
                {
                    'name': 'port',
                    'title': 'Web Server Port',
                    'type': 'integer',
                    'default': DEFAULT_SSL_PORT
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'pool_size',
                    'title': 'Scan Thread Pool Size',
                    'type': 'integer',
                    'required': True,
                    'default': DEFAULT_POOL_SIZE
                },
                {
                    'name': 'fetch_ssllabs',
                    'title': 'Fetch Data from SSL Labs',
                    'type': 'bool',
                    'required': True,
                    'default': False
                }
            ],
            'required': [
                'port', 'pool_size', 'fetch_ssllabs'
            ],
            'type': 'array'
        }
        return add_node_selection(action_schema, WEBSCAN_PLUGIN_NAME)

    @staticmethod
    def default_config() -> dict:
        default_schema = {'port': DEFAULT_SSL_PORT, 'https_proxy': None}
        return add_node_default(default_schema, WEBSCAN_PLUGIN_NAME)

    def __run(self) -> EntitiesResult:
        for chunk in chunks(CHUNK_SIZE, self._internal_axon_ids):
            adapter_unique_name = PluginBase.Instance._get_adapter_unique_name(WEBSCAN_PLUGIN_NAME, self.action_node_id)
            action_data = {
                'internal_axon_ids': chunk,
                'client_config': self._config
            }
            action_result = self._plugin_base._trigger_remote_plugin(
                adapter_unique_name,
                job_name='enrich',
                priority=True,
                blocking=True,
                data=action_data
            )
            action_result = action_result.json()

            if action_result.get('status') == 'error':
                raise RuntimeError(action_result['message'])

            yield from (
                self.prettify_output(k, v)
                for k, v
                in action_result.items()
            )

    def _webscan_fail(self, reason):
        reason = str(reason)
        reason = f'Error while running Webscan Enrichment: {reason}'
        yield from generic_fail(internal_axon_ids=self._internal_axon_ids, reason=reason)

    def _run(self) -> EntitiesResult:
        try:
            yield from self.__run()
        except Exception as e:
            logger.exception('Error while running Webscan Enrichment')
            yield from self._webscan_fail(e)
