import logging

from funcy import chunks
from axonius.clients.wmi_query.consts import (
    ACTION_TYPES, SCAN_ACTION_SCHEMA, SCAN_CHUNK_SIZE)
from axonius.consts.plugin_consts import WMI_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from reports.action_types.action_type_base import (ActionTypeBase,
                                                   add_node_default,
                                                   add_node_selection)

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=W0212


class RunWMIScan(ActionTypeBase):
    """
    Runs a WMI Scan using wmi adapter
    """

    @staticmethod
    def prettify_output(id_, result: dict) -> EntityResult:
        value = result['value']
        success = result['success']
        return EntityResult(id_, success, value)

    @staticmethod
    def config_schema() -> dict:
        return add_node_selection(SCAN_ACTION_SCHEMA)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({})

    def _trigger_wmi_adapter(self, node_id: str, axon_ids: dict) -> dict:
        action_data = {
            'internal_axon_ids': axon_ids,
            'client_config': self._config
        }
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(WMI_PLUGIN_NAME, node_id)
        action_result = self._plugin_base._trigger_remote_plugin(adapter_unique_name,
                                                                 priority=True,
                                                                 blocking=True,
                                                                 data=action_data,
                                                                 job_name=ACTION_TYPES.scan)
        action_result = action_result.json()
        if action_result.get('status') == 'error':
            raise RuntimeError(action_result['message'])
        return action_result

    def _run(self) -> EntitiesResult:
        node_id = self.action_node_id

        for chunk in chunks(SCAN_CHUNK_SIZE, self._internal_axon_ids):
            # pylint: disable=protected-access
            logger.info(f'Sending wmi scan request to {len(chunk)} devices using wmi adapter')
            action_result = self._trigger_wmi_adapter(node_id, chunk)

            yield from (
                self.prettify_output(k, v)
                for k, v
                in action_result.items()
            )
