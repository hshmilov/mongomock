import logging

from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default
from reports.action_types.base.carbonblack_utils import carbonblack_action, ADAPTER_NAME

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackIsolateAction(ActionTypeBase):
    """
    Isolate a CarbonBlack response device
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
        Performs a carbonblack action
        :param action: The action to perform (isolate, unisolate)
        :param entity_type: The entity type
        :param internal_axon_ids: list of axonius devices to isolate
        :return:
        """
        return carbonblack_action('isolate_device', self._get_entities_from_view({
            'internal_axon_id': 1,
            'adapters.client_used': 1,
            'adapters.data.id': 1,
            'adapters.plugin_name': 1
        }), self.action_node_id)
