import sys

from axonius.entities import EntityType
from axonius.utils.debug import redprint
from testing.services.plugins.gui_service import GuiService


def usage():
    print(f'Usage: {sys.argv[0]} [devices/users] [adapter_plugin_name_from] [adapter_plugin_name_to] [dry/wet]')
    print(f'Example: {sys.argv[0]} devices service_now service_now_akana dry')


def set_all_queries_from_chart_recursively(item, from_str: str, to_str: str):
    """
    Goes over a query recursively, changing from_str to to_str
    :return:
    """

    if isinstance(item, dict):
        for sub_key, sub_item in item.items():
            item[sub_key] = set_all_queries_from_chart_recursively(sub_item, from_str, to_str)
        return item
    if isinstance(item, list):
        return [set_all_queries_from_chart_recursively(x, from_str, to_str) for x in item]
    if isinstance(item, str) and from_str in item:
        return item.replace(from_str, to_str)

    return item


# pylint: disable=protected-access, unbalanced-tuple-unpacking
def main():
    try:
        _, asset_type, adapter_from, adapter_to, action = sys.argv
    except Exception:
        return -1

    gui_service = GuiService()
    if asset_type == 'devices':
        collection = gui_service._entity_views_map[EntityType.Devices]
    elif asset_type == 'users':
        collection = gui_service._entity_views_map[EntityType.Users]
    else:
        raise ValueError(f'Invalid value {asset_type}')

    assert '_adapter' not in adapter_from, f'{adapter_from} should not contain "_adapter"'
    assert '_adapter' not in adapter_to, f'{adapter_to} should not contain "_adapter"'

    queries_to_fix = []
    for doc in collection.find({'query_type': 'saved', 'archived': False}):
        if f'{adapter_from}_adapter' in doc.get('view', {}).get('query', {}).get('filter', ''):
            print(f'Found query {doc.get("name")!r}')
            queries_to_fix.append(doc)

    if action != 'wet':
        return 0

    print(f'Changing {adapter_from} to {adapter_to}...')
    for doc in queries_to_fix:
        doc = set_all_queries_from_chart_recursively(doc, f'{adapter_from}_adapter', f'{adapter_to}_adapter')
        # print(json.dumps(doc, indent=4, default=lambda o:str(o)))

    for doc in queries_to_fix:
        collection.replace_one(
            {
                '_id': doc['_id']
            },
            doc
        )

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        redprint(f'Exception: {str(e)}')
        print(usage())
        sys.exit(-1)
