"""
Backup various things

WARNING - I PUT IT HERE JUST FOR FUTURE REFERENCE - THIS IS NOT NECESSARILY WORKING.
"""
import json
import sys

from bson import ObjectId

from axonius.consts.gui_consts import USERS_COLLECTION
from axonius.modules.plugin_settings import Consts
from testing.services.plugins import core_service

from axonius.utils.debug import greenprint

SHOULD_BACKUP_ADAPTER_CLIENTS = True
SHOULD_BACKUP_ADAPTER_ADVANCED_SETTINGS = True
SHOULD_BACKUP_ENFORCEMENT_CENTER = True


def usage():
    print(f'{sys.argv[0]} [backup/restore] [filename]')


def backup(filename: str):
    cs = core_service.CoreService()
    db = cs.db.client

    backup_dict = {
        'adapters': {},
        'adapter_configurable_configs': [],
        'enforcements': [],
        'actions': []
    }
    if SHOULD_BACKUP_ADAPTER_CLIENTS:
        for db_name in db.database_names():
            if 'adapter' in db_name:
                if not list(db[db_name]['clients'].find({})):
                    # Empty adapter, not interesting
                    continue

                backup_dict['adapters'][db_name] = {}
                for collection_name in db[db_name].collection_names():
                    print(f'Writing {db_name}/{collection_name}...')
                    content = list(db[db_name][collection_name].find({}))

                    if collection_name == 'devices_data':
                        continue
                    if collection_name == 'clients':
                        # This is a special collection - we need to decrypt this
                        for client in content:
                            if 'client_config' in client:
                                cs.decrypt_dict(client['client_config'])

                    backup_dict['adapters'][db_name][collection_name] = content

        greenprint(f'Backed up {len(backup_dict["adapters"])} adapter dbs')

    if SHOULD_BACKUP_ADAPTER_ADVANCED_SETTINGS:
        for cc in db['core'][Consts.AllConfigurableConfigs].find({}):
            if 'adapter' in cc['plugin_name']:
                backup_dict['adapter_configurable_configs'].append(cc)

        greenprint(f'Backed up {len(backup_dict["adapter_configurable_configs"])} adapter configurable configs.')

    if SHOULD_BACKUP_ENFORCEMENT_CENTER:
        all_reports = list(db['reports']['reports'].find({}))
        for report in all_reports:
            backup_dict['enforcements'].append(report)

        greenprint(f'Backed up {len(all_reports)} reports.')

        all_saved_actions = list(db['reports']['saved_actions'].find({}))
        for action in all_saved_actions:
            cs.decrypt_dict(action['action']['config'])
            backup_dict['actions'].append(action)

        greenprint(f'Backed up {len(all_saved_actions)} saved actions.')

    with open(filename, 'wt') as f:
        f.write(json.dumps(backup_dict, indent=4, default=lambda o: str(o)))

    return 0


def restore(filename: str):
    cs = core_service.CoreService()
    db = cs.db.client

    with open(filename, 'rt') as f:
        backup_dict = json.loads(f.read())

    for db_name, db_collections in backup_dict.get('adapters', {}).items():
        for collection_name, collection_data in db_collections.items():
            greenprint(f'Restoring {db_name}/{collection_name}')
            if collection_name == 'clients':
                if collection_data:
                    for client in collection_data:
                        if 'client_config' in client:
                            cs.encrypt_dict(db_name, client['client_config'])

            try:
                db[db_name][collection_name].delete_many({})
            except Exception:
                pass
            if collection_data:
                db[db_name][collection_name].insert(collection_data)

    acc = backup_dict.get('adapter_configurable_configs', [])
    greenprint(f'Restoring {len(acc)} adapter configurable configs')
    for cc in acc:
        assert 'adapter' in cc['plugin_name']
        cc.pop('_id', None)
        db['core'][Consts.AllConfigurableConfigs].replace_one(
            {
                'plugin_name': cc['plugin_name'],
                'config_name': cc['config_name']
            },
            cc,
            upsert=True
        )

    creator_id = db['gui'][USERS_COLLECTION].find_one({'user_name': 'admin'})
    if not creator_id:
        raise ValueError(f'Error: No such user admin! please specify a different user.')
    creator_id = creator_id['_id']

    enforcements = backup_dict.get('enforcements', [])
    actions = backup_dict.get('actions', [])
    greenprint(f'Restoring {len(enforcements)} enforcements')
    if enforcements:
        try:
            db['reports']['reports'].delete_many({})
        except Exception:
            pass
        for en in enforcements:
            en['_id'] = ObjectId(en['_id'])
            en['user_id'] = creator_id
            en['updated_by'] = creator_id
            db['reports']['reports'].insert_one(en)

    greenprint(f'Restoring {len(actions)} actions')
    if actions:
        try:
            db['reports']['saved_actions'].delete_many({})
        except Exception:
            pass
        for action in actions:
            action['_id'] = ObjectId(action['_id'])
            cs.encrypt_dict('reports', action['action']['config'])
            db['reports']['saved_actions'].insert_one(action)


def main():
    try:
        _, mode, filename = sys.argv
    except Exception:
        usage()
        return -1

    if mode == 'backup':
        return backup(filename)
    elif mode == 'restore':
        return restore(filename)
    else:
        raise ValueError(f'Invalid mode {mode!r}')


if __name__ == '__main__':
    sys.exit(main())
