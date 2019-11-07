"""
This lets us export a backup of Axonius / import a backup of Axonius.
Our backup includes everything:
- Full MongoDB backup
- .axonius_settings
- volatile config of containers

Requirements:
- The destination machine must have the exact same version of Axonius

How to backup:
1. shut down system, but db
2. sudo ./devops/scripts/backup/axonius_backup_restore.sh backup backup.zip pass
How to restore:
1. shut down system, but db
2. sudo ./devops/scripts/backup/axonius_backup_restore.sh restore backup.zip pass

after each:
3. ./axonius.sh system up --all --prod --skip
"""
import glob
import sys
import argparse
import zipfile
import subprocess
import os

from pathlib import Path

from axonius.utils.debug import greenprint, yellowprint, redprint

AXONIUS_SETTINGS_PATH = '/home/ubuntu/cortex/.axonius_settings'
PLUGIN_VOLATILE_CONFIG_GLOB = '/var/lib/docker/volumes/*_data/_data/plugin_volatile_config.ini'
AXONIUS_RESTORE_FOLDER = 'axonius_restore'
DB_ZIP_PATH = 'db/db.gz'


def exec_cmd(cmd):
    subprocess.check_call(cmd)


# pylint: disable=too-many-statements
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

    if os.geteuid() != 0:
        redprint(f'Error - you have to be root')
        return -1

    if args.mode == 'backup':
        if Path(args.file).exists():
            raise ValueError(f'Error - backup file {args.file} exists')
        greenprint(f'Backing up mongo...')
        exec_cmd(
            [
                'docker', 'exec', 'mongo', 'sh', '-c',
                'exec mongodump --username="ax_user" --password="ax_pass" --gzip --archive=/db_backup.gz'
            ]
        )
        greenprint(f'Transferring file from within the mongo container..')
        exec_cmd(['docker', 'cp', 'mongo:/db_backup.gz', '/home/ubuntu/db_backup.gz'])
        greenprint(f'Deleting backup from the mongo container')
        exec_cmd(['docker', 'exec', 'mongo', 'rm', '/db_backup.gz'])

        with zipfile.ZipFile(args.file, 'w') as zf:
            zf.write(f'/home/ubuntu/db_backup.gz', arcname=DB_ZIP_PATH)
            os.unlink('/home/ubuntu/db_backup.gz')
            greenprint(f'Backing up .axonius_settings')
            for file_path in (glob.glob(os.path.join(AXONIUS_SETTINGS_PATH, '*')) +
                              glob.glob(os.path.join(AXONIUS_SETTINGS_PATH, '.*'))):
                file_name = file_path.split('/')[-1]
                print(file_name)
                zf.write(file_path, arcname=f'.axonius_settings/{file_name}')

            greenprint(f'Backing up plugin_volatile_config.ini files')
            for file_path in glob.glob(PLUGIN_VOLATILE_CONFIG_GLOB):
                print(file_path)
                zf.write(file_path, arcname=f'plugin_volatile_config/{file_path}')
        greenprint('Done')

    if args.mode == 'restore':
        with zipfile.ZipFile(args.file, 'r') as zf:
            for zip_file_path in zf.namelist():
                component, *file_path = zip_file_path.split(os.path.sep)

                if zip_file_path == DB_ZIP_PATH:
                    greenprint(f'restoring db')
                    zf.extract(zip_file_path, path=AXONIUS_RESTORE_FOLDER)
                    greenprint(f'copying file to mongo')
                    db_file_path = os.path.join(AXONIUS_RESTORE_FOLDER, DB_ZIP_PATH)
                    exec_cmd(
                        ['docker', 'cp', db_file_path, 'mongo:/db_restore.gz']
                    )
                    os.unlink(db_file_path)
                    greenprint(f'Restoring db')
                    exec_cmd(
                        [
                            'docker', 'exec', 'mongo', 'sh', '-c',
                            'exec mongorestore --username="ax_user" --password="ax_pass" --gzip '
                            '--archive=/db_restore.gz'
                        ]
                    )
                    exec_cmd(['docker', 'exec', 'mongo', 'rm', '/db_restore.gz'])

                elif component == '.axonius_settings':
                    os_file_path = os.path.join(AXONIUS_SETTINGS_PATH, os.path.sep.join(file_path))
                    greenprint(f'extracting {os_file_path}')
                    with zf.open(zip_file_path, 'r') as zf_file:
                        with open(os_file_path, 'wb') as os_file:
                            os_file.write(zf_file.read())

                elif component == 'plugin_volatile_config':
                    os_file_path = os.path.join(os.path.sep, os.path.sep.join(file_path))
                    greenprint(f'extracting {os_file_path}')
                    with zf.open(zip_file_path, 'r') as zf_file:
                        with open(os_file_path, 'wb') as os_file:
                            os_file.write(zf_file.read())

                else:
                    yellowprint(f'Warning - Invalid component {component}!')

        greenprint(f'Done with restore. Please restart the system')
    return 0


if __name__ == '__main__':
    exit(main())
