import logging

from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.action_type_base import ActionTypeBase
from reports.action_types.base.cybereason_utils import cybereason_action

logger = logging.getLogger(f'axonius.{__name__}')


class CybereasonUnisolateAction(ActionTypeBase):
    """
    Isolate a Cybereason response device
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'malop_id',
                    'title': 'Malware OP ID',
                    'type': 'string'
                }
            ],
            'required': [
                'malop_id'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'malop_id': None,
        }

    def _run(self) -> EntitiesResult:
        """
        Performs a Cybereason action
        :param action: The action to perform (isolate, unisolate)
        :param entity_type: The entity type
        :param internal_axon_ids: list of axonius devices to isolate
        :return:
        """
        return cybereason_action('unisolate_device', self._get_entities_from_view({
            'internal_axon_id': 1,
            'adapters.client_used': 1,
            'adapters.data.pylum_id': 1,
            'adapters.plugin_name': 1
        }), self._config['malop_id'])
