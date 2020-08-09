import datetime
import sys
from getpass import getpass

import funcy

from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME
from axonius.utils.axonius_query_language import parse_filter
from testing.services.plugins.gui_service import GuiService

ENTITIES_TO_UNLINK_CHUNKS = 15


def main():
    try:
        _, entity, username = sys.argv     # pylint: disable=unbalanced-tuple-unpacking
    except Exception:
        print(f'Usage: {sys.argv[0]} [devices/users] [local_user_username]\n')
        return -1

    if entity not in ['devices', 'users']:
        print('Entity must be devices/users')
        return -1

    password = getpass(f'Enter password for local user {username!r}: ')

    gui = GuiService()
    if gui.login_user({'user_name': username, 'password': password}).status_code != 200:
        print(f'Wrong username or password')
        return -1

    aql = input('Enter AQL:')

    try:
        query = parse_filter(aql)
    except Exception:
        print(f'Invalid query, please try again: {aql!r}')
        return -1

    if entity == 'devices':
        db = gui.db.get_collection(AGGREGATOR_PLUGIN_NAME, 'devices_db')
        unlink = gui.unlink_devices
    elif entity == 'users':
        db = gui.db.get_collection(AGGREGATOR_PLUGIN_NAME, 'users_db')
        unlink = gui.unlink_users
    else:
        print(f'Error: entity must be devices or users')
        return -1

    print(f'Calculating number of entities by query "{aql}"..')
    all_entities = list(db.find(query, projection={'_id': 0, 'internal_axon_id': 1}))
    count_of_entities = len(all_entities)
    answer = input(f'Entities found: {count_of_entities}. Are you sure you would like to continue? [type yes]')
    if answer != 'yes':
        print(f'Goodbye.')
        return -1

    entities_unlinked = 0
    for chunk in funcy.chunks(ENTITIES_TO_UNLINK_CHUNKS, all_entities):
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
