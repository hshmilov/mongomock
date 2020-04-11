import datetime
import json
import os
import sys

import funcy

from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME
from testing.services.plugins.gui_service import GuiService

ENTITIES_TO_UNLINK_CHUNKS = 15


def main():
    try:
        _, entity, query = sys.argv     # pylint: disable=unbalanced-tuple-unpacking
    except Exception:
        print(f'Usage: {sys.argv[0]} [type] [mongo_query]\n')
        return -1

    if 'username' not in os.environ or 'password' not in os.environ:
        print(f'Please put username and password in env')

    if not query:
        print(f'Error: did not get query')
        return -1

    if query == 'all':
        query = {'$where': 'this.adapters.length > 1'}
    else:
        query = json.loads(query)

    gui = GuiService()

    if entity == 'devices':
        db = gui.db.get_collection(AGGREGATOR_PLUGIN_NAME, 'devices_db')
        unlink = gui.unlink_devices
    elif entity == 'users':
        db = gui.db.get_collection(AGGREGATOR_PLUGIN_NAME, 'users_db')
        unlink = gui.unlink_users
    else:
        print(f'Error: entity must be devices or users')
        return -1

    print(f'Calculating number of entities by query "{query}"..')
    count_of_entities = db.find(query).count()
    answer = input(f'Entities found: {count_of_entities}. Are you sure you would like to continue? [yes]')
    if answer != 'yes':
        print(f'Goodbye.')
        return -1

    entities_unlinked = 0
    gui.login_user({'user_name': os.environ['username'], 'password': os.environ['password']})
    for chunk in funcy.chunks(ENTITIES_TO_UNLINK_CHUNKS, db.find(query, projection={'_id': 0, 'internal_axon_id': 1})):
        internal_axon_ids_to_unlink = [document['internal_axon_id'] for document in chunk]
        unlink(internal_axon_ids=internal_axon_ids_to_unlink).raise_for_status()
        entities_unlinked += ENTITIES_TO_UNLINK_CHUNKS

        if entities_unlinked % (10 * ENTITIES_TO_UNLINK_CHUNKS) == 0:
            now = datetime.datetime.now().strftime('%H:%M:%S')
            print(f'[{now}] Finished {entities_unlinked} / {count_of_entities} '
                  f'({round(entities_unlinked / count_of_entities, 2)}%)')

    print(f'Done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
