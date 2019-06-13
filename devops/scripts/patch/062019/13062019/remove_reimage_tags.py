"""
We changed the logics of reimage-tags, but the labels are still in the field. This script removes all old fields.
"""
import sys

from axonius.entities import EntityType
from services.plugins.aggregator_service import AggregatorService


def main():
    try:
        _, action = sys.argv    # pylint: disable=unbalanced-tuple-unpacking
        assert action in ['dry', 'wet']
    except Exception:
        print(f'Usage: {sys.argv[0]} dry/wet')
        return -1

    print(f'Starting on --{action}-- mode')

    aggregator = AggregatorService()

    i = 0
    for entity_type in EntityType:
        entities_db = aggregator._entity_db_map[entity_type]    # pylint: disable=protected-access
        for entity in entities_db.find({}):
            for tag in entity.get('tags') or []:
                label_type = tag.get('type')
                label_name = tag.get('name')
                label_data = tag.get('data')
                label_value = tag.get('label_value')
                if label_type == 'label' and (label_name.lower().startswith('reimaged by ')
                                              or label_value.lower().startswith('reimaged by ')):
                    print(f'{i} - {entity_type}: {entity["internal_axon_id"]}: '
                          f'Found bad label: {label_name}')
                    i += 1
                    if action == 'wet':
                        entities_db.update_one(
                            {
                                'internal_axon_id': entity['internal_axon_id'],
                                'tags': {
                                    '$elemMatch': {
                                        'name': label_name,
                                        'type': label_type,
                                        'data': label_data,
                                        'label_value': label_value
                                    }
                                }
                            },
                            {'$set': {'tags.$.data': False, 'tags.$.label_value': ''}}
                        )

    print('Done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
