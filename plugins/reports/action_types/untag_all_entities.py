import logging

from axonius.utils.gui_helpers import add_labels_to_entities
from reports.action_types.action_type_base import ActionTypeBase, generic_success
from reports.enforcement_classes import EntitiesResult

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=W0212


class UntagAllEntitiesAction(ActionTypeBase):
    """
    Untags all entities
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
        db = self._plugin_base._entity_db_map[self._entity_type]
        namespace = self._plugin_base._namespaces[self._entity_type]
        add_labels_to_entities(db, namespace, self._internal_axon_ids, [self._config['tag_name']], True)
        return generic_success(self._internal_axon_ids)
