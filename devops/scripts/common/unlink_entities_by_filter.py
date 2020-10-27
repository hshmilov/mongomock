import datetime
import sys
from getpass import getpass

import funcy

from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME
from axonius.entities import EntityType
from axonius.modules.query.axonius_query import get_axonius_query_singleton
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

    if entity == 'users':
        entity_type = EntityType.Users
        db = gui.db.get_collection(AGGREGATOR_PLUGIN_NAME, 'users_db')
        unlink = gui.unlink_users
    elif entity == 'devices':
        entity_type = EntityType.Devices
        db = gui.db.get_collection(AGGREGATOR_PLUGIN_NAME, 'devices_db')
        unlink = gui.unlink_devices

    password = getpass(f'Enter password for local user {username!r}: ')

    gui = GuiService()
    if gui.login_user({'user_name': username, 'password': password}).status_code != 200:
        print(f'Wrong username or password')
        return -1

    aql = input('Enter AQL:')

    try:
        query = get_axonius_query_singleton().parse_aql_filter(aql, entity_type=entity_type)
    except Exception:
        print(f'Invalid query, please try again: {aql!r}')
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
                  f'({round(entities_unlinked / count_of_entities, 2) * 100}%)')

    print(f'Done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
