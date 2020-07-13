"""
How to use:
1.
"""
import sys

from axonius.consts.plugin_consts import CORE_UNIQUE_NAME
from axonius.utils.debug import greenprint, redprint
from testing.services.plugins.mongo_service import MongoService


def usage():
    print(f'''Usage:
{sys.argv[0]} show [plugin_name]
{sys.argv[0]} swap [first plugin_unique_name] [second plugin_unique_name]
    '''.strip())


def main():
    ms = MongoService()
    core_db = ms.client[CORE_UNIQUE_NAME]
    action = sys.argv[1]

    nodes_by_id = {x['node_id']: x for x in core_db['nodes_metadata'].find({})}
    if action == 'show':
        plugin_name = sys.argv[2]
        all_plugins = list(core_db['configs'].find({'plugin_name': plugin_name}))
        if not all_plugins:
            raise ValueError(f'plugin name {plugin_name} not found in db.')

        for i, plugin in enumerate(all_plugins):
            node = nodes_by_id[plugin['node_id']]
            print(f'{i}. {plugin["plugin_unique_name"]} | '
                  f'on {node["node_id"]!r} ({node["node_name"]!r} / {",".join(node["ips"])})')
    elif action == 'update':
        pun_1 = sys.argv[2]
        pun_2 = sys.argv[3]
        pun_1_in_db = core_db['configs'].find_one({'plugin_unique_name': pun_1})
        pun_2_in_db = core_db['configs'].find_one({'plugin_unique_name': pun_2})

        assert pun_1_in_db, f'plugin unique name {pun_1} not found!'
        assert pun_2_in_db, f'plugin unique name {pun_2} not found!'
        assert pun_1_in_db['plugin_name'] == pun_2_in_db['plugin_name'], 'Those plugins are not of the same adapter!'
        assert pun_1_in_db['node_id'] != pun_2_in_db['node_id'], 'Those plugins have the same node id!'

        print(f'Swapping node_id')
        core_db['configs'].update_one(
            {
                'plugin_unique_name': pun_1,
            },
            {
                '$set': {
                    'node_id': pun_2_in_db['node_id']
                }
            }
        )

        core_db['configs'].update_one(
            {
                'plugin_unique_name': pun_2,
            },
            {
                '$set': {
                    'node_id': pun_1_in_db['node_id']
                }
            }
        )

        greenprint(f'Done! please run the following on both nodes: ')
        greenprint(f'sudo ./axonius.sh adapter {pun_1_in_db["plugin_name"]} up --restart --prod --hard --yes-hard')

    else:
        usage()
        return -1

    return 0


if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except Exception as e:
        redprint(f'Error: {str(e)}')
        # traceback.print_exc()
        usage()
        sys.exit(-1)
