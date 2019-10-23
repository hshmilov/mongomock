import logging

from funcy import chunks

from axonius.consts.plugin_consts import WEBSCAN_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.plugin_base import PluginBase
from reports.action_types.action_type_base import ActionTypeBase, generic_fail, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

CHUNK_SIZE = 30000
# pylint: disable=protected-access


class WebscanEnrichment(ActionTypeBase):
    @staticmethod
    def prettify_output(id_, result: dict) -> EntityResult:
        value = result['value']
        success = result['success']
        return EntityResult(id_, success, value)

    @staticmethod
    def config_schema() -> dict:
        action_schema = {}
        return add_node_selection(action_schema, WEBSCAN_PLUGIN_NAME)

    @staticmethod
    def default_config() -> dict:
        default_schema = {}
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
        yield generic_fail(internal_axon_ids=self._internal_axon_ids, reason=reason)

    def _run(self) -> EntitiesResult:
        try:
            yield from self.__run()
        except Exception as e:
            logger.exception('Error while running Webscan Enrichment')
            yield from self._webscan_fail(e)
