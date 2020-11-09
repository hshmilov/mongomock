import argparse
import shlex
import shutil
import subprocess
import sys
import tarfile
from distutils import dir_util
from json import loads
from pathlib import Path
from zipfile import ZipFile

from pymongo import MongoClient

from axonius.consts.plugin_consts import BYTES_TO_MB
from axonius.consts.system_consts import (AXONIUS_SETTINGS_PATH, CORTEX_PATH,
                                          METADATA_PATH, NODE_ID_ABSOLUTE_PATH,
                                          PYRUN_PATH_HOST)
from axonius.db.db_client import DB_HOST, DB_PASSWORD, DB_USER
from axonius.logging.audit_helper import AuditType
from axonius.modules.common import AxoniusCommon
from axonius.utils.debug import greenprint, redprint, yellowprint
from devops.axonius_system import main as axonius
from scripts.instances.delete_instances_user import LOGGED_IN_MARKER_PATH
from scripts.watchdog.watchdog_main import WATCHDOG_MAIN_SCRIPT_PATH

RESTORE_FOLDER = Path(CORTEX_PATH) / 'restore'
RESTORE_WORKING_PATH = Path(CORTEX_PATH) / 'infrastructures/database/scripts/restore'
RESTORE_DOT_AXON_SETTINGS_PATH = RESTORE_WORKING_PATH / '.axonius_settings'
RESTORE_METADATA_PATH = RESTORE_WORKING_PATH / '__build_metadata'
MONGO_RESTORE_DIR = '/scripts/restore'
RESTORE_TIMEOUT = 60 * 60 * 4

'''

Restore Setting :
=================
- the backup file expected to be located at ~/cortex/restore.
- backup content will be decrypt and extract at ~/cortex/infrastructures/database/scripts/restore and will
  be deleted at the end

Restore preconditions:
======================
1. current half of host available space is greater then 10 times backup archive size.
2. axonius backup version must match current axonius installation
3. note that it is mandatory to not perform sign-up operation.
4. if backup node_id is different then reset wave key

during restore axonius system will shutdown and restarted .

* in case of instances and master IP or DNS changed then node(s) need to re-register

https://axonius.atlassian.net/browse/PROD-1000

'''

BANNER = (
    r'''
              __   ______  _   _ _____ _    _  _____            _____  ______  _____ _______ ____  _____  ______
        /\    \ \ / / __ \| \ | |_   _| |  | |/ ____|          |  __ \|  ____|/ ____|__   __/ __ \|  __ \|  ____|
       /  \    \ V / |  | |  \| | | | | |  | | (___    ______  | |__) | |__  | (___    | | | |  | | |__) | |__
      / /\ \    > <| |  | | . ` | | | | |  | |\___ \  |______| |  _  /|  __|  \___ \   | | | |  | |  _  /|  __|
     / ____ \  / . \ |__| | |\  |_| |_| |__| |____) |          | | \ \| |____ ____) |  | | | |__| | | \ \| |____
    /_/    \_\/_/ \_\____/|_| \_|_____|\____/|_____/           |_|  \_\______|_____/   |_|  \____/|_|  \_\______|

    ....axonius system restore v1.0

    '''
)


def get_free_space_in_mb():
    return round(shutil.disk_usage(RESTORE_FOLDER).free / BYTES_TO_MB, 2)


def get_backupfile_size(filename):
    return round((RESTORE_FOLDER / filename).stat().st_size / BYTES_TO_MB, 2)


class AxoniusRestore:
    def __init__(self, filename, passphrase, delete_backup_file=False, skip_version_check=False, ci=False):
        if not (RESTORE_FOLDER / filename).exists():
            raise RuntimeError(f'backup file name {filename} not found')
        self.file_name = filename
        self.passphrase = passphrase
        self._delete_backup_file = delete_backup_file
        self._host_node_id = NODE_ID_ABSOLUTE_PATH.read_text()
        self._axon_version = loads(Path(METADATA_PATH).read_text()).get('Version') or 'None'
        self._is_signup = LOGGED_IN_MARKER_PATH.exists()
        self._is_backup_on_different_node = False
        self._skip_version_check = skip_version_check
        self._ci_testing = ci
        backup_file_size = get_backupfile_size(self.file_name)
        free_space = get_free_space_in_mb()

        yellowprint((f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
                     f'Backup file name  {self.file_name}\n'
                     f'Backup File size {backup_file_size}/MB\n'
                     f'Current available free space is {free_space}/MB\n'
                     f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'))

        # predict the size of extract db size ( avg compress level is 10 times)
        # will not consume more then half of current free space
        if backup_file_size * 10 > free_space / 2:
            raise RuntimeError('not enough free space to proceed with restore process ')

    def check_if_backup_on_different_node(self):
        """
        compare backup node_id to current host node_id
        when restoring on different node then need to reset wave
        """
        backup_node_id = (RESTORE_DOT_AXON_SETTINGS_PATH / '.node_id').read_text()
        print(f'Installation node id = {self._host_node_id}\nBackup node id  = {backup_node_id}')
        self._is_backup_on_different_node = self._host_node_id != backup_node_id
        print(f' is_backup_on_different_node - > {self._is_backup_on_different_node}')

    def untar(self):
        greenprint(f'Unpacking Tar File {self.file_name} . . . ')
        with tarfile.open(RESTORE_FOLDER / self.file_name) as backup_tar_file:
            backup_tar_file.extractall(path=RESTORE_WORKING_PATH)
        yellowprint(f'Unpacking Tar File {self.file_name} is done')

    @staticmethod
    def mongorestore(is_aggregator=False):
        """
        call docker exec mongorestore on mongo service
        support archive and collection dump.
        mongorestore mode: --drop --preserveUUID
        container restore folder = /scripts/restore
        :param is_aggregator: restore aggregator collection using archive file.
        """
        uri = (f'"mongodb://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/'
               f'{"aggregator?authSource=admin" if is_aggregator else "?authSource=admin"}"')

        cmd = (
            f'docker exec mongo mongorestore --drop --preserveUUID --uri={uri} '
            f'{f"--gzip --archive={MONGO_RESTORE_DIR}/aggregator.gz" if is_aggregator else f"{MONGO_RESTORE_DIR}/dump"}'
        )
        yellowprint(f'##### mongorestore cmd: {cmd} ##### ')
        subprocess.check_call(shlex.split(cmd), timeout=RESTORE_TIMEOUT)

    @staticmethod
    def copy_axon_settings():
        dir_util.copy_tree(src=str(RESTORE_DOT_AXON_SETTINGS_PATH),
                           dst=str(AXONIUS_SETTINGS_PATH),
                           preserve_symlinks=True,
                           preserve_mode=True,
                           verbose=1)

    def verify_axonius_versions(self):
        """
        compare running axonius version match the db backup version
        _skip_version_check -> internal to be used by internal build or testing
        """
        if self._skip_version_check:
            redprint('skipping backup version check !')
            return

        backup_axon_version = loads(RESTORE_METADATA_PATH.read_text()).get('Version') or 'None'
        yellowprint(f'Verifying backup version "{backup_axon_version}" match install version "{self._axon_version}"')
        if backup_axon_version != self._axon_version or self._axon_version == 'None':
            raise RuntimeError('backup version does not match installed version')

    @staticmethod
    def _watchdog_tasks(action=''):
        # until permission issues fix explicit call to stop watchdog as root
        # https://axonius.atlassian.net/browse/AX-8746
        subprocess.check_call(shlex.split(f' {PYRUN_PATH_HOST} {WATCHDOG_MAIN_SCRIPT_PATH} {action}'))

    @staticmethod
    def reset_weave():
        yellowprint('*** reset weave network   ***')
        subprocess.check_call(shlex.split('weave reset'))

    def _decrypt(self, encrypted_filename: str):
        """
        GPG command wrapper
        """
        try:
            decrypted_filename = encrypted_filename.split('.gpg')[0]
            gpg_cmd = (f'gpg --output {decrypted_filename} '
                       f'--decrypt --passphrase={self.passphrase} {encrypted_filename}')

            gpg_decrypt = subprocess.Popen(shlex.split(gpg_cmd),
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           cwd=RESTORE_WORKING_PATH)

            yellowprint(f'decrypting {encrypted_filename} this may take a while . . . .')
            cmd_out, cmd_err = gpg_decrypt.communicate(timeout=60 * 60 * 2)

        except subprocess.TimeoutExpired:
            gpg_decrypt.kill()
            cmd_out, cmd_err = gpg_decrypt.communicate()
            raise Exception(f'gpg command pipeline with encryption timeout!'
                            f' stderr={cmd_err} output={cmd_out}')

        if gpg_decrypt.returncode != 0:
            raise Exception(f' backup decryption failed return code={gpg_decrypt.returncode}\n'
                            f'stderr={cmd_err}\n output={cmd_out}')

        (RESTORE_WORKING_PATH / encrypted_filename).unlink()

    @staticmethod
    def _unzip(filename):
        with ZipFile(RESTORE_WORKING_PATH / filename, 'r') as zip_file:
            yellowprint(f'extracting {filename}  . . . ')
            zip_file.extractall(path=RESTORE_WORKING_PATH)
        (RESTORE_WORKING_PATH / filename).unlink()

    def restore(self):
        if RESTORE_WORKING_PATH.exists():
            shutil.rmtree(RESTORE_WORKING_PATH)
        RESTORE_WORKING_PATH.mkdir()
        self.untar()
        self.verify_axonius_versions()
        self._decrypt('db_backup.zip.gpg')
        self._unzip('db_backup.zip')
        self.check_if_backup_on_different_node()
        yellowprint(f'current installation been signup:{self._is_signup} New Node: {self._is_backup_on_different_node}')
        if self._is_signup and self._is_backup_on_different_node:
            raise RuntimeError('A clean host is required (no previous sign-up) when restoring on'
                               ' a different host from the backup instance.')
        self._decrypt('aggregator.gz.gpg')
        greenprint('*** Axonius System is shutting down  ***')
        axonius(shlex.split('system down --all'))
        self._watchdog_tasks(action='stop')
        self.copy_axon_settings()
        if self._is_backup_on_different_node:
            self.reset_weave()
        axonius(shlex.split('service mongo up --prod'))

        # aggregator archive file
        self.mongorestore(is_aggregator=True)
        # all other dbs
        self.mongorestore()
        # why not just exclude mongo on system start ?
        # to avoid the following issue 'find requires authentication' when core starting up
        axonius(shlex.split('service mongo down'))
        #
        # on CI TEST not all services are pre register upon installation vs official Export build.
        # to avoid issues with restarting services and to save time, only ci adapters are started .
        #
        axon_system_start_cmd = (
            f'system up --prod {"--adapters json_file ad" if self._ci_testing else "--all"} '
            f'{"--env DB_RESTORE_NEW_NODE=TRUE" if self._is_backup_on_different_node else ""} '
        )

        print(f'*** Starting Axonius after restore : {axon_system_start_cmd} ***')
        axonius(shlex.split(axon_system_start_cmd))
        self._watchdog_tasks(action='start')
        self.audit_restore_done()
        if self._delete_backup_file:
            (RESTORE_FOLDER / self.file_name).unlink()
        self._watchdog_tasks(action='start')

    def audit_restore_done(self):
        try:
            AxoniusCommon().add_activity_msg('restore', 'restored', {
                'filename': self.file_name,
            }, AuditType.Info)

        except Exception as e:
            redprint(f'failed to update response completed audit message {e}')


def clean_restore_folder():
    shutil.rmtree(RESTORE_WORKING_PATH)


def main(args=None):
    parser = argparse.ArgumentParser()

    greenprint(BANNER)

    parser.add_argument('-f', '--file', action='store',  help='Backup File Name to restore', required=True)
    parser.add_argument('-p', '--passphrase', help='decrypt backup passphrase', required=True)
    parser.add_argument('-del', '--delete_backup_file', help='delete backup tar file when done', action='store_true')
    parser.add_argument('-svc', '--skip_version_check', help=argparse.SUPPRESS, action='store_true')
    parser.add_argument('-si', '--skip_interactive', help=argparse.SUPPRESS, action='store_true')
    parser.add_argument('-ci',  help=argparse.SUPPRESS, action='store_true')

    try:
        args = parser.parse_args(args)
        if not args.skip_interactive:
            response = input('Restoring the system from a backup will delete all content from the system.\r\n'
                             'Are you sure you want to continue? [Yes/No]')
            if not response.lower() == 'yes':
                print('Restore aborted . . . !')
                sys.exit(0)
    except AttributeError:
        redprint(parser.usage())
        sys.exit(1)

    try:
        # check we running on axonius installation
        if not NODE_ID_ABSOLUTE_PATH.exists() and NODE_ID_ABSOLUTE_PATH.stat().st_size == 0:
            redprint(' ("Invalid Host to restore on : axonius installation must exists !")    ')
            return 1

        # check host not been signup before

        restore_handler = AxoniusRestore(args.file,
                                         args.passphrase,
                                         args.delete_backup_file,
                                         args.skip_version_check,
                                         args.ci)

        greenprint('Start Restore process . . . ')
        restore_handler.restore()
        greenprint('Restore completed successfully ')
        return 0
    except Exception as e:
        redprint(f'restore exit with error {e}')
        return 1
    finally:
        if RESTORE_FOLDER.exists():
            clean_restore_folder()


if __name__ == '__main__':
    exit(main())
