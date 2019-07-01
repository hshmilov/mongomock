from collections import defaultdict
from pymongo import MongoClient

# Checks the Axonius instance to find irregularities in the DB.
# It checks whether there are "stray" DBs, i.e. DBs whose name doesn't match up with any registered plugin
# It also checks whether there are any duplicates of specific plugins in the core/configs DB.

# This is a R/O script: It doesn't change anything, only reports back.

# Written as part of https://axonius.atlassian.net/browse/AX-4431

# You should grep for "Found leftovers" or "Found duplications" to get a binary result of whether there are any issues.


def log(fmt, *args, **kwargs):
    print(f'[VERIFY_INTEGRITY]: {fmt}', *args, **kwargs)


def main():
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
    plugin_unique_names = {x['plugin_unique_name'] for x in registered_plugins}

    leftovers = {x for x in dbs if x not in plugin_unique_names} - {'core', 'config'}
    if not leftovers:
        log('No leftovers')
    else:
        log(f'Found leftovers: ({len(leftovers)}) ' + ', '.join(leftovers))
        for x in leftovers:
            log(f'Letover collections {x}: ' + ', '.join(db[x].list_collection_names()))

    # Leftovers should be deleted!

    # finding duplicates in the core configs

    by_plugin_name = defaultdict(list)
    for x in registered_plugins:
        by_plugin_name[x['plugin_name']].append(x)

    # Plugins that we're updating to become a singleton, let's verify this as well
    plugins_in_question = ['reports', 'general_info', 'execution',
                           'static_correlator', 'static_users_correlator', 'device_control']

    for x in plugins_in_question:
        instances = by_plugin_name[x]
        if len(instances) > 1:
            unique_names = {plugin['plugin_unique_name'] for plugin in instances}
            log(f'Found duplications ({len(unique_names)}): {x}: ' + ', '.join(unique_names))


if __name__ == '__main__':
    main()
