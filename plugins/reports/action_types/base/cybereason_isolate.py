import logging

from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default
from reports.action_types.base.cybereason_utils import cybereason_action, ADAPTER_NAME

logger = logging.getLogger(f'axonius.{__name__}')


class CybereasonIsolateAction(ActionTypeBase):
    """
    Isolate a Cybereason response device
    """

    @staticmethod
    def config_schema() -> dict:
        return add_node_selection({}, ADAPTER_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
        }, ADAPTER_NAME)

    def _run(self) -> EntitiesResult:
        """
        Performs a cybereason action
        :param action: The action to perform (isolate, unisolate)
        :param entity_type: The entity type
        :param internal_axon_ids: list of axonius devices to isolate
        :return:
        """
        return cybereason_action('isolate_device', self._get_entities_from_view({
            'internal_axon_id': 1,
            'adapters.client_used': 1,
            'adapters.data.pylum_id': 1,
            'adapters.plugin_name': 1
        }), self.action_node_id)
