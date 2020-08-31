from axonius.utils.gui_helpers import is_subjson, parse_entity_fields


# pylint:disable=too-many-statements, too-many-locals, too-many-branches, too-many-nested-blocks
def merge_entities_fields(entities_data: dict, fields: dict):
    """
        find all entities that are subset of other entities, and merge them.

        this code is a port of the mergeData.js file.

    :param entities_data:  the entities to do the merge on
    :param fields:  schema dictionary mapped by name
    :return: entities merged by subsets
    """

    string_fields = [item['name'] for item in fields.values() if item['type'] == 'string' and '.' not in item['name']]
    local_data = [parse_entity_fields(entity_data, fields.keys()) for entity_data in entities_data]

    total_excluded_set = set()

    for field_name in string_fields:
        excluded_set = {}
        values_set = set()

        normalizes_data = [item.get(field_name) for item in local_data if item]

        for index, data_item in enumerate(normalizes_data):
            if not data_item:
                continue

            if data_item in values_set:
                excluded_set.pop(data_item, None)
            else:
                excluded_set[data_item] = index
                values_set.add(data_item)

        total_excluded_set = set(total_excluded_set).union(excluded_set.values())

    result = [local_data[index] for index in total_excluded_set]
    for index, subset in enumerate(local_data):

        if subset is None or index in total_excluded_set:
            continue
        found = False

        for superset_index, superset in enumerate(result):
            if superset is None:
                continue

            merge_adapters = False

            if is_subjson(superset, subset):
                result[superset_index] = subset
                found = True
                merge_adapters = True
            elif is_subjson(subset, superset):
                found = True
                merge_adapters = True

            if merge_adapters and\
                    'adapters' in superset and\
                    'adapters' in subset and\
                    'adapters' in result[superset_index]:
                result[superset_index]['adapters'] = sorted(list(
                    set(superset['adapters']).union(subset['adapters']).union(result[superset_index]['adapters'])
                ))

        if not found:
            result.append(subset)

    if result and 'adapters' in result[0]:
        result.sort(key=lambda x: x['adapters'], reverse=False)

    return result
