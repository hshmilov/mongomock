import sys
from collections import defaultdict
from pymongo import MongoClient

# Fixes the DB.
# Some plugins which are supposed to be singletons still have multiple DBs and registration events.
# This script will mark all leftover DBs as such so they don't intefere with the work.
# It will also mark such registration events in the core/configs DB

# Written as part of https://axonius.atlassian.net/browse/AX-4431


def log(fmt, *args, **kwargs):
    print(f'[DELETE_UNUSED_DATABASES]: {fmt}', *args, **kwargs)


def deprecate_a_leftover_db(plugin_unique_name: str):
    db = MongoClient('127.0.0.1:27017', username='ax_user', password='ax_pass')
    admin_db = db['admin']
    for collection_name in db[plugin_unique_name].list_collection_names():
        admin_db.command({
            'renameCollection': f'{plugin_unique_name}.{collection_name}',
            'to': f'DEPRECATED_{plugin_unique_name}.{collection_name}'
        })

    doc = db['core']['configs'].find_one_and_delete({
        'plugin_unique_name': plugin_unique_name
    })
    if doc:
        db['core']['configs_deprecated'].insert_one(doc)


def main(wet: bool):
    db = MongoClient('127.0.0.1:27017', username='ax_user', password='ax_pass')
    dbs = db.list_database_names()  # this just returns a list string
    try:
        dbs.remove('admin')  # this doesn't remove the DB from mongo, it only removes it from the list :P
    except ValueError:
        pass
    try:
        dbs.remove('local')
    except ValueError:
        pass
    log(f'Databases: ({len(dbs)}) ' + ', '.join(dbs))

    registered_plugins = list(db['core']['configs'].find({}))

    # finding duplicates in the core configs

    by_plugin_name = defaultdict(list)
    for x in registered_plugins:
        by_plugin_name[x['plugin_name']].append(x)

    # Plugins that we're updating to become a singleton
    plugins_in_question = ['reports', 'general_info', 'execution',
                           'static_correlator', 'static_users_correlator', 'device_control']

    for x in plugins_in_question:
        instances = by_plugin_name[x]
        if len(instances) > 1:
            unique_names = {plugin['plugin_unique_name'] for plugin in instances}
            log(f'Found duplications ({len(unique_names)}): {x}: ' + ', '.join(unique_names))

            last_seen = max(instances, key=lambda x: x['last_seen'])
            leftover_dbs = [
                x['plugin_unique_name']
                for x
                in instances
                if x['plugin_unique_name'] != last_seen['plugin_unique_name']
            ]

            log(f'{last_seen["plugin_unique_name"]} is the newest, olds are all others: ' +
                ', '.join(leftover_dbs))

            if wet:
                for leftover in leftover_dbs:
                    log(f'Deprecating {leftover}')
                    deprecate_a_leftover_db(leftover)


if __name__ == '__main__':
    wet = False
    if len(sys.argv) > 1:
        if sys.argv[1] == 'wet':
            wet = True
    log('Running ' + ('wet' if wet else 'dry') + '!')
    main(wet)
