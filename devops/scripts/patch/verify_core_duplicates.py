from pymongo import MongoClient


# Checks core/config to find illegal duplicates

# This is a R/O script: It doesn't change anything, only reports back.

# Written as part of https://axonius.atlassian.net/browse/AX-4491

def log(fmt, *args, **kwargs):
    print(f'[VERIFY_CORE_DUPLICATES]: {fmt}', *args, **kwargs)


def main():
    db = MongoClient('127.0.0.1:27017', username='ax_user', password='ax_pass')

    registered_plugins = list(db['core']['configs'].find({}))
    plugin_unique_names = [x['plugin_unique_name'] for x in registered_plugins]

    log(f'plugins unique names: {plugin_unique_names}')

    duplicates = list(plugin_unique_names)
    for i in set(plugin_unique_names):
        duplicates.remove(i)

    if duplicates:
        log(f'FOUND PLUGIN UNIQUE NAME DUPLICATES!: {duplicates}')

    plugin_name_and_node = [(x['plugin_name'], x['node_id']) for x in registered_plugins]
    log(f'plugins names and node ids: {plugin_name_and_node}')

    duplicates = list(plugin_name_and_node)
    for i in set(plugin_name_and_node):
        duplicates.remove(i)

    if duplicates:
        log(f'FOUND PLUGIN NAME / NODE ID DUPLICATES!: {duplicates}')


if __name__ == '__main__':
    main()
