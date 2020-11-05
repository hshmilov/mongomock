#!/usr/bin/env python3.6
"""
This script installs the system from scratch (using --first-time) or as an upgrade.
    * no parameters necessary...
    * it is intended to run as the __main__.py script for the final zip installer created by make.py
"""
import argparse
import datetime
import glob
import os
import shutil
import stat
import subprocess
import sys
import time

from pathlib import Path

from utils import (AXONIUS_DEPLOYMENT_PATH,
                   AXONIUS_OLD_ARCHIVE_PATH,
                   SOURCES_FOLDER_NAME,
                   AutoOutputFlush,
                   current_file_system_path,
                   print_state,
                   run_cmd,
                   chown_folder, verify_storage_requirements)

TIMESTAMP = datetime.datetime.now().strftime('%y%m%d-%H%M')

DEPLOYMENT_FOLDER_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'deployment')
STATE_OUTPUT_PATH = os.path.join(os.path.dirname(current_file_system_path), 'encrypted.state')
ARCHIVE_PATH = AXONIUS_OLD_ARCHIVE_PATH.format(TIMESTAMP)
TEMPORAL_PATH = f'{AXONIUS_DEPLOYMENT_PATH}_TEMP_{TIMESTAMP}'
INSTANCES_SCRIPT_PATH = 'devops/scripts/instances'
WEAVE_PATH = '/usr/local/bin/weave'
DELETE_INSTANCES_USER_CRON_SCRIPT_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCES_SCRIPT_PATH,
                                                      'delete_instances_user.py')
SYSTEM_BOOT_CRON_SCRIPT_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'machine_boot.sh')
INSTANCES_SETUP_SCRIPT_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCES_SCRIPT_PATH, 'setup_node.sh')
INSTANCE_SETTINGS_DIR_NAME = '.axonius_settings'
UPLOADED_FILES_DIR_NAME = 'uploaded_files'
BOOT_CONFIGURATION_NAME = Path('boot_configuration_script.tar')
AXONIUS_SETTINGS_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCE_SETTINGS_DIR_NAME)
UPLOADED_FILES_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, UPLOADED_FILES_DIR_NAME)
INSTANCE_IS_MASTER_MARKER_PATH = os.path.join(AXONIUS_SETTINGS_PATH, '.logged_in')
BOOTED_FOR_PRODUCTION_MARKER_PATH = os.path.join(AXONIUS_SETTINGS_PATH, '.booted_for_production')
INSTANCE_CONNECT_USER_PASSWORD = 'M@ke1tRain'
PYTHON_INSTALLER_LOCK_DIR = Path('/tmp/ax-locks/')
PYTHON_INSTALLER_LOCK_FILE = PYTHON_INSTALLER_LOCK_DIR / 'python_installer.lock'
PYTHON_INSTALLED_HTTPD_PATH = Path(AXONIUS_DEPLOYMENT_PATH) / 'testing/services/plugins/httpd_service/httpd/upgrade.py'

CHMOD_FILES = [
    INSTANCES_SETUP_SCRIPT_PATH,
    os.path.join(AXONIUS_DEPLOYMENT_PATH, 'axonius.sh'),
    os.path.join(AXONIUS_DEPLOYMENT_PATH, 'prepare_python_env.sh'),
    os.path.join(AXONIUS_DEPLOYMENT_PATH, 'devops/scripts/log_utils/raw_log.py'),
    os.path.join(AXONIUS_DEPLOYMENT_PATH, 'devops/scripts/discover_now.py'),
]


def check_lock_file(path):
    """
    checks if lock file exists and not older than LOCK_TOO_OLD_THRESH. If it is, it deletes it.
    :return:
    """
    if not path.is_file():
        return False
    if time.time() - path.stat().st_ctime > 5 * 60 * 60:
        path.unlink()
        return False
    return True


def is_inside_container():
    return Path('/.dockerenv').exists()


def main():
    metadata = ''
    if os.geteuid() != 0:
        print(f'Please run as root!')
        return False
    with AutoOutputFlush():
        success = False
        try:
            if check_lock_file(PYTHON_INSTALLER_LOCK_FILE):
                print(f'Install is already in progress')
            else:
                if not PYTHON_INSTALLER_LOCK_DIR.is_dir():
                    PYTHON_INSTALLER_LOCK_DIR.mkdir(exist_ok=True)
                PYTHON_INSTALLER_LOCK_FILE.touch()
                success = start_install_flow()

            try:
                metadata_path = Path(AXONIUS_DEPLOYMENT_PATH) / 'shared_readonly_files' / '__build_metadata'
                metadata = metadata_path.read_text()
            except Exception:
                print(f'Failed to read metadata')

        finally:
            status = 'success' if success else 'failure'
            if is_inside_container():
                print(f'Upgrader completed inside container - {status} {metadata}')
            else:
                print(f'Upgrader completed - {status} {metadata}')

            if PYTHON_INSTALLER_LOCK_FILE.is_file():
                PYTHON_INSTALLER_LOCK_FILE.unlink()
            if success:
                sys.exit(0)
            else:
                sys.exit(1)


def start_install_flow():
    parser = argparse.ArgumentParser()
    parser.add_argument('--first-time', action='store_true', default=False, help='First Time install')
    parser.add_argument('--no-research', action='store_true', default=False, help='Sudo password')
    parser.add_argument('--do-not-verify-storage', action='store_true', default=False, help='Skip storage verification')
    parser.add_argument('--inside-container', action='store_true', default=False, help='Inside container section')
    parser.add_argument('--master-only', action='store_true', default=False,
                        help='Upgrade only this system even if nodes are connected')
    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        return True
    start = time.time()
    no_research = args.no_research
    do_not_verify_storage = args.do_not_verify_storage
    master_only = args.master_only
    inside_container = args.inside_container
    if not do_not_verify_storage:
        verify_storage_requirements()
    install(args.first_time, no_research, master_only, inside_container)
    print_state(f'Done, took {int(time.time() - start)} seconds')
    return True


def push_old_instances_settings():
    print_state('Copying old settings (weave encryption key, master marker and first boot marker')
    if os.path.exists(os.path.join(TEMPORAL_PATH, INSTANCE_SETTINGS_DIR_NAME)):
        os.rename(os.path.join(TEMPORAL_PATH, INSTANCE_SETTINGS_DIR_NAME),
                  AXONIUS_SETTINGS_PATH)


def load_new_source():
    print_state('Loading new source folder')
    installer_folder_source_path = f'{SOURCES_FOLDER_NAME}/'
    os.makedirs(AXONIUS_DEPLOYMENT_PATH, exist_ok=True)
    # Extracting source files from currently running python zip to AXONIUS_DEPLOYMENT_PATH
    for source_path in glob.glob(f'{installer_folder_source_path}/**', recursive=True):
        path = source_path[len(installer_folder_source_path):]
        full_path = os.path.join(AXONIUS_DEPLOYMENT_PATH, path)
        if os.path.isdir(source_path):
            if not os.path.isdir(full_path):
                os.makedirs(full_path)
            os.chmod(full_path, 0o755)
            continue
        shutil.copy2(source_path, full_path)
        # chmod +x for .sh files
        if full_path.endswith('.sh') and sys.platform.startswith('linux'):
            os.chmod(full_path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC |
                     stat.S_IXGRP | stat.S_IXOTH | stat.S_IRGRP | stat.S_IROTH)

    push_old_instances_settings()


def install_requirements():
    print_state('Install requirements')
    pip3_path = 'python3.6 -m pip'
    requirements = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'requirements.txt')
    packages = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'deployment', 'packages')
    subprocess.check_call(f'{pip3_path} -V'.split(' '))
    args = [*pip3_path.split(' '), 'install', '--upgrade', 'pip', '--find-links', packages,
            '--no-index',           # Don't use internet access
            '--no-cache',           # Don't use local cache
            '--ignore-installed']   # Dont uninstall dist-packages (make python go mad)
    subprocess.check_call(args)
    args = [*pip3_path.split(' '), 'install', '-r', requirements, '--find-links', packages,
            '--no-index',           # Don't use internet access
            '--no-cache',           # Don't use local cache
            '--ignore-installed']   # Dont uninstall dist-packages (make python go mad)
    subprocess.check_call(args)


def validate_old_state():
    if not os.path.isdir(AXONIUS_DEPLOYMENT_PATH):
        name = os.path.basename(AXONIUS_DEPLOYMENT_PATH)
        msg = f'{name} folder wasn\'t found at {AXONIUS_DEPLOYMENT_PATH} (missing --first-time ?)'
        print(msg)
        raise Exception(msg)

    chown_folder(AXONIUS_DEPLOYMENT_PATH)

    if not os.path.exists(WEAVE_PATH):
        name = os.path.basename(WEAVE_PATH)
        print(f'{name} binary wasn\'t found at {WEAVE_PATH}. please install weave and try again.')
        raise FileNotFoundError(f'{name} binary wasn\'t found at {WEAVE_PATH}')


def set_special_permissions():
    # Adding write permissions on .axonius_settings so node_maker can touch a new node.marker
    os.makedirs(AXONIUS_DEPLOYMENT_PATH, exist_ok=True)
    cmd = f'chmod -R o-w {AXONIUS_DEPLOYMENT_PATH}'
    run_cmd(cmd.split())

    # Adding write and execute permissions on all the scripts node_maker uses.
    for current_file in CHMOD_FILES:
        cmd = f'chmod +xr {current_file}'
        run_cmd(cmd.split())


def create_boot_config_file():
    try:
        if BOOT_CONFIGURATION_NAME.is_file() and BOOT_CONFIGURATION_NAME.stat().st_size > 0:
            os.makedirs(UPLOADED_FILES_PATH, exist_ok=True)
            BOOT_CONFIGURATION_NAME.replace(Path(UPLOADED_FILES_PATH, BOOT_CONFIGURATION_NAME))
    except Exception as e:
        print(f'Error creating boot file config {e}')


def create_pth():
    # running this script as executable because can't easily import in at this stage
    create_pth_cmd = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'devops', 'create_pth.py')
    return subprocess.check_output(['python3', create_pth_cmd]).decode('utf-8').strip()


def copy_installer_to_httpd():
    ppid = os.getppid()
    installer_cmdline = Path('/proc/{0}/cmdline'.format(ppid)).read_text().strip('\x00').split('\x00')
    part = ''
    for part in installer_cmdline:
        if part.startswith('--') or part in Path('/etc/shells').read_text().strip().split('\n')[1:]:
            continue
        if Path(part).exists():
            break
    installer_path = (Path(os.getenv('ORIGINAL_PWD')) / part).absolute()
    print(f'installer_path: {installer_path}')
    if installer_path:
        try:
            shutil.copy2(str(installer_path), str(PYTHON_INSTALLED_HTTPD_PATH))
        except Exception as e:
            print(f'Error copying installation file to httpd path')
    else:
        print('Could not find installation file')


def install(first_time, no_research, master_only, inside_container=False):
    if inside_container:
        from deployment.with_venv_install import after_venv_activation
        after_venv_activation(first_time, no_research, master_only, current_file_system_path)
        return
    if not first_time:
        validate_old_state()
        os.rename(AXONIUS_DEPLOYMENT_PATH, TEMPORAL_PATH)

    load_new_source()
    pth_file_location = create_pth()
    # install_requirements()
    create_boot_config_file()
    if not first_time:
        copy_installer_to_httpd()

    try:
        from deployment.install_utils import setup_host, load_images, launch_axonius_manager, set_logrotate
    except ModuleNotFoundError:
        # Hack to reload the pth file contents without actually restart the python instance
        # pylint: disable=expression-not-assigned
        [sys.path.append(path) for path in Path(pth_file_location).read_text().strip().split('\n')]
        from deployment.install_utils import setup_host, load_images, launch_axonius_manager, set_logrotate
    setup_host()
    # We load for the first time only to get the axonius-manager image
    load_images()
    os.system(f'mv images.tar {AXONIUS_DEPLOYMENT_PATH}/images.tar')
    set_logrotate()
    launch_axonius_manager()
    extra_args = f'{"--first-time" if first_time else ""} {"--no-research" if no_research else ""} ' \
                 f'{"--master-only" if master_only else ""}'
    os.system(f'docker exec axonius-manager /bin/bash '
              f'-c "python3 ./devops/create_pth.py; python3 ./deployment/install.py --inside-container {extra_args}"')

    # Cleanup
    os.remove(f'{AXONIUS_DEPLOYMENT_PATH}/images.tar')

    print('Restarting axonius-manager')
    # Cleaning all hanging exec process before
    launch_axonius_manager()


if __name__ == '__main__':
    # important note: This is not called during the install phase. The actual entrypoint is the function main
    with AutoOutputFlush():
        main()
