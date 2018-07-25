import os
import psutil
import sys
import pymongo
from datetime import datetime


def get_memory_usage_in_mb():
    return psutil.Process(os.getpid()).memory_info().rss / (1024**2)


def main():
    try:
        _, username, password = sys.argv
    except Exception:
        print(f"Usage: {sys.argv[0]} username password")
        return -1

    connection_line = "mongodb://{user}:{password}@{addr}:{port}".format(user=username,
                                                                         password=password,
                                                                         addr="127.0.0.1",
                                                                         port="27017")
    client = pymongo.MongoClient(connection_line)

    windows_devices = client["aggregator"]["devices_db"].find(
        {"adapters.plugin_name": "active_directory_adapter"},
        projection={'internal_axon_id': True,
                    'adapters.data.id': True,
                    'adapters.plugin_unique_name': True,
                    'adapters.client_used': True,
                    'adapters.data.hostname': True,
                    'adapters.data.name': True,
                    'tags': True})

    def get_last_execution_time(d):
        for tag in [t for t in d.get("tags", []) if t.get('type') == 'adapterdata']:
            lse = tag.get('data', {}).get('general_info_last_success_execution')
            if lse is not None and type(lse) == datetime:
                return lse

        return datetime(1970, 1, 1, 0, 0, 0)

    print(f"Memory usage before list & sort: {get_memory_usage_in_mb()}mb")
    windows_devices = list(windows_devices)
    print(f"Got {len(windows_devices)} devices.")
    print(f"Memory usage after list: {get_memory_usage_in_mb()}mb")
    windows_devices.sort(key=get_last_execution_time)
    print(f"Memory usage after list & sort: {get_memory_usage_in_mb()}mb")

    for d in windows_devices[-200:]:
        print(get_last_execution_time(d))


if __name__ == '__main__':
    sys.exit(main())
