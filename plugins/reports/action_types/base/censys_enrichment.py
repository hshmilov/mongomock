import logging

from axonius.consts.plugin_consts import CENSYS_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.censys.consts import (ACTION_SCHEMA, BASE_DEFAULTS_SCHEMA)
from axonius.plugin_base import PluginBase
from reports.action_types.action_type_base import ActionTypeBase, generic_fail, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=protected-access


class CensysEnrichment(ActionTypeBase):
    @staticmethod
    def prettify_output(id_, result: dict) -> EntityResult:
        value = result['value']
        success = result['success']
        return EntityResult(id_, success, value)

    @staticmethod
    def config_schema() -> dict:
        return add_node_selection(ACTION_SCHEMA, CENSYS_PLUGIN_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default(BASE_DEFAULTS_SCHEMA, CENSYS_PLUGIN_NAME)

    def _trigger_censys_adapter(self):
        adapter_unique_name = PluginBase.Instance._get_adapter_unique_name(CENSYS_PLUGIN_NAME, self.action_node_id)
        action_data = {'internal_axon_ids': self._internal_axon_ids, 'client_config': self._config}
        action_result = self._plugin_base._trigger_remote_plugin(
            adapter_unique_name,
            priority=True,
            blocking=True,
            data=action_data
        )
        action_result = action_result.json()

        if action_result.get('status') == 'error':
            raise RuntimeError(action_result['message'])

        return action_result

    def _censys_fail(self, reason):
        reason = str(reason)
        reason = f'Error while running Censys Enrichment: {reason}'
        return generic_fail(internal_axon_ids=self._internal_axon_ids, reason=reason)

    def __run(self) -> EntitiesResult:
        action_result = self._trigger_censys_adapter()
        return [self.prettify_output(k, v) for k, v in action_result.items()]

    def _run(self) -> EntitiesResult:
        try:
            return self.__run()
        except Exception as e:
            logger.exception('Error while running Censys Enrichment')
            return self._censys_fail(e)
