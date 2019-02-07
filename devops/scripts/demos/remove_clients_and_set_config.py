import sys

import pymongo


def main():
    mc = pymongo.MongoClient('localhost', username='ax_user', password='ax_pass')
    for db in mc.database_names():
        print(f'{db}: removing clients and setting big last fetch...')
        mc[db].clients.remove({})
        mc[db].configurable_configs.update(
            {'config_name': 'AdapterBase'},
            {'$set': {
                'config.last_fetched_threshold_hours': 100000,
                'config.user_last_fetched_threshold_hours': 100000
            }}
        )

    print(f'Done. Please restart the whole system for the changes to take effect in the memory (flush from db)')


if __name__ == '__main__':
    sys.exit(main())
