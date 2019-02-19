import logging

from reports.action_types.action_type_base import ActionTypeBase
from reports.enforcement_classes import EntitiesResult
from reports.action_types.base.carbonblack_utils import carbonblack_action

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackUnisolateAction(ActionTypeBase):
    """
    Isolate a CarbonBlack response device
    """

    @staticmethod
    def config_schema() -> dict:
        return {
        }

    @staticmethod
    def default_config() -> dict:
        return {
        }

    def _run(self) -> EntitiesResult:
        """
        Performs a carbonblack action
        :param action: The action to perform (isolate, unisolate)
        :param entity_type: The entity type
        :param internal_axon_ids: list of axonius devices to isolate
        :return:
        """
        return carbonblack_action('unisolate_device', self._get_entities_from_view({
            'internal_axon_id': 1,
            'adapters.client_used': 1,
            'adapters.data.id': 1,
            'adapters.plugin_name': 1
        }))
