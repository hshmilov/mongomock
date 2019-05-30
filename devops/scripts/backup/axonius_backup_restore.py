"""
This lets us export a backup of Axonius / import a backup of Axonius.
How to backup:
source ./prepare_python_env.sh; python3 -u ./devops/scripts/backup/axonius_backup_restore.py backup backup.zip pass

How to restore:
1. source ./prepare_python_env.sh; python3 -u ./devops/scripts/backup/axonius_backup_restore.py restore backup.zip pass
2. ./axonius.sh system up --all --prod --restart
"""
import sys
import argparse
import zipfile
from pathlib import Path
from itertools import cycle

from bson.json_util import dumps, loads
from testing.services.plugins import core_service


def xor_message(message, key):
    return bytes([c ^ k for c, k in zip(message, cycle(key))])


def main():
    parser = argparse.ArgumentParser()

    # Required positional argument
    parser.add_argument('mode', choices=['backup', 'restore'], help='Whether to backup or restore')
    parser.add_argument('file', help='File to backup or restore')
    parser.add_argument('password', help='password')

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    db = core_service.CoreService().db.client

    if args.mode == 'backup':
        if Path(args.file).exists():
            raise ValueError(f'Error - backup file {args.file} exists')
        with zipfile.ZipFile(args.file, 'w') as zf:
            for db_name in db.database_names():
                # First version of this script backup's only adapters
                if 'adapter' in db_name:
                    for collection_name in db[db_name].collection_names():
                        print(f'Writing {db_name}/{collection_name}...')
                        zf.writestr(
                            f'db/{db_name}/{collection_name}',
                            xor_message(dumps(db[db_name][collection_name].find({})).encode('utf-8'),
                                        args.password.encode('utf-8'))
                        )
        print(f'Done with backup.')

    if args.mode == 'restore':
        with zipfile.ZipFile(args.file, 'r') as zf:
            for file_path in zf.namelist():
                _, db_name, collection_name = file_path.split('/')
                with zf.open(file_path, 'r') as zf_file:
                    collection_data = loads(xor_message(zf_file.read(), args.password.encode('utf-8')))

                print(f'Restoring {db_name}/{collection_name}')
                try:
                    db[db_name][collection_name].delete_many({})
                except Exception:
                    pass
                db[db_name][collection_name].insert(collection_data)

        print(f'Done with restore. Please restart the system')


if __name__ == '__main__':
    exit(main())
