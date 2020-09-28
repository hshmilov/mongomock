import logging

from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default
from reports.action_types.base.endpoint_utils import endpoint_action

logger = logging.getLogger(f'axonius.{__name__}')


class CybereasonTagAction(ActionTypeBase):
    """
    Tag a Cybereason response device
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'tag_name',
                    'title': 'Tag name',
                    'type': 'string'
                },
                {
                    'name': 'tag_value',
                    'title': 'Tag value',
                    'type': 'string'
                },
            ],
            'required': [
                'tag_name', 'tag_value'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'tag_name': None,
            'tag_value': None
        })

    def _run(self) -> EntitiesResult:
        """
        Performs a cybereason action
        :param action: The action to perform (isolate, unisolate, tag_sensor)
        :param entity_type: The entity type
        :param internal_axon_ids: list of axonius devices to isolate
        :return:
        """
        tags_dict = {self._config['tag_name']: self._config['tag_value']}
        return endpoint_action('cybereason_adapter', 'tag_sensor', self._get_entities_from_view({
            'internal_axon_id': 1,
            'adapters.client_used': 1,
            'adapters.data.name': 1,
            'adapters.plugin_name': 1
        }), self.action_node_id, tags_dict=tags_dict)
