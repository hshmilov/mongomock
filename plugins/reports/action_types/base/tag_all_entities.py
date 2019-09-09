import logging

from axonius.utils.gui_helpers import add_labels_to_entities
from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.action_type_base import ActionTypeBase, generic_success

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=W0212


class TagAllEntitiesAction(ActionTypeBase):
    """
    Tags all entities
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'tag_name',
                    'title': 'Tag name',
                    'type': 'string'
                },
            ],
            'required': [
                'tag_name'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'tag_name': ''
        }

    def _run(self) -> EntitiesResult:
        if not self._internal_axon_ids:
            return []
        namespace = self._plugin_base._namespaces[self._entity_type]
        add_labels_to_entities(namespace, self._internal_axon_ids, [self._config['tag_name']], False, is_huge=True)
        return generic_success(self._internal_axon_ids)
