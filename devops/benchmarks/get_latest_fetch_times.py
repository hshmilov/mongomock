import pymongo


# Get the latest time and speed of fetching of all adapters from the DB

def main():
    c = pymongo.MongoClient('mongodb://ax_user:ax_pass@127.0.0.1:40028')

    # Get all adapters PUNs
    plugins = [x['plugin_unique_name']
               for x
               in c['core']['configs'].find() if
               '_adapter' in x['plugin_unique_name']]

    for x in plugins:
        db = c[x]['triggerable_history']
        task = db.find_one({
            'job_name': 'insert_to_db'
        }, sort=[('started_at', pymongo.DESCENDING)])
        if task:
            import json
            try:
                result = json.loads(task['result'])
                count = result['devices_count'] + result['users_count']
                seconds = (task['finished_at'] - task['started_at']).total_seconds()
                print(f'{x}: {seconds} seconds, has {count} adapters, {count / seconds} adapters/second')
            except Exception as e:
                print(f'err with {x}: {e}')


if __name__ == '__main__':
    main()
