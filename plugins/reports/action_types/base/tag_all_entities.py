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
                    'type': 'string',
                    'enum': [],
                    'source': {
                        'key': 'all-tags',
                        'options': {
                            'allow-custom-option': True
                        }
                    }
                },
                {
                    'name': 'should_remove_tag_from_no_queried',
                    'title': 'Remove tag from entities not found in the Saved Query results',
                    'type': 'bool',
                }
            ],
            'required': [
                'tag_name'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'tag_name': '',
            'should_remove_tag_from_no_queried': False
        }

    def _run(self) -> EntitiesResult:
        # Tag
        if not self._internal_axon_ids:
            return []
        namespace = self._plugin_base._namespaces[self._entity_type]

        # Remove the tag from unqueried entities
        if self._config.get('should_remove_tag_from_no_queried', False):
            # Find entities to remove tag from
            db_cursor = self.entity_db.find({
                'tags.label_value': self._config['tag_name']

            }, projection={
                '_id': 0,
                'internal_axon_id': 1,
            })
            diff_calc = set(entity['internal_axon_id'] for entity in db_cursor)
            diff_calc = diff_calc.difference(self._internal_axon_ids)

            # Remove the tags from unqueried entities
            add_labels_to_entities(namespace, diff_calc, [self._config['tag_name']], True, is_huge=True)

        # Add the tag to queried entities
        add_labels_to_entities(namespace, self._internal_axon_ids, [self._config['tag_name']], False, is_huge=True)

        return generic_success(self._internal_axon_ids)
