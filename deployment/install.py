#!/usr/bin/env python3.6
"""
This script installs the system from scratch (using --first-time) or as an upgrade.
    * no parameters necessary...
    * it is intended to run as the __main__.py script for the final zip installer created by make.py
"""
import argparse
import datetime
import os
import stat
import subprocess
import sys
import time

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
VENV_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'venv')
STATE_OUTPUT_PATH = os.path.join(os.path.dirname(current_file_system_path), 'encrypted.state')
ARCHIVE_PATH = AXONIUS_OLD_ARCHIVE_PATH.format(TIMESTAMP)
TEMPORAL_PATH = f'{AXONIUS_DEPLOYMENT_PATH}_TEMP_{TIMESTAMP}'
INSTANCES_SCRIPT_PATH = 'devops/scripts/instances'
WEAVE_PATH = '/usr/local/bin/weave'
DELETE_INSTANCES_USER_CRON_SCRIPT_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCES_SCRIPT_PATH,
                                                      'delete_instances_user.py')
SYSTEM_BOOT_CRON_SCRIPT_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'machine_boot.sh')
INSTANCES_SETUP_SCRIPT_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCES_SCRIPT_PATH, 'setup_node.py')
INSTANCE_SETTINGS_DIR_NAME = '.axonius_settings'
AXONIUS_SETTINGS_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCE_SETTINGS_DIR_NAME)
INSTANCE_IS_MASTER_MARKER_PATH = os.path.join(AXONIUS_SETTINGS_PATH, '.logged_in')
BOOTED_FOR_PRODUCTION_MARKER_PATH = os.path.join(AXONIUS_SETTINGS_PATH, '.booted_for_production')
INSTANCE_CONNECT_USER_NAME = 'node_maker'
INSTANCE_CONNECT_USER_PASSWORD = 'M@ke1tRain'

CHMOD_FILES = [
    INSTANCES_SETUP_SCRIPT_PATH,
    os.path.join(AXONIUS_DEPLOYMENT_PATH, 'axonius.sh'),
    os.path.join(AXONIUS_DEPLOYMENT_PATH, 'prepare_python_env.sh'),
    os.path.join(AXONIUS_DEPLOYMENT_PATH, 'devops/scripts/log_utils/raw_log.py'),
    os.path.join(AXONIUS_DEPLOYMENT_PATH, 'devops/scripts/discover_now.py'),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--first-time', action='store_true', default=False, help='First Time install')
    parser.add_argument('--no-research', action='store_true', default=False, help='Sudo password')
    parser.add_argument('--do-not-verify-storage', action='store_true', default=False, help='Skip storage verification')

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    start = time.time()
    no_research = args.no_research
    do_not_verify_storage = args.do_not_verify_storage

    if not do_not_verify_storage:
        verify_storage_requirements()

    if os.geteuid() != 0:
        # we are not root
        print(f'Please run as root!')
        return

    install(args.first_time, no_research)
    print_state(f'Done, took {int(time.time() - start)} seconds')


def push_old_instances_settings():
    print_state('Copying old settings (weave encryption key, master marker and first boot marker')
    if os.path.exists(os.path.join(TEMPORAL_PATH, INSTANCE_SETTINGS_DIR_NAME)):
        os.rename(os.path.join(TEMPORAL_PATH, INSTANCE_SETTINGS_DIR_NAME),
                  AXONIUS_SETTINGS_PATH)


def load_new_source():
    from utils import zip_loader
    # this code run from _axonius.py zip, and assumes that zip loader exist
    assert zip_loader is not None

    print_state('Loading new source folder')
    zip_folder_source_path = f'{SOURCES_FOLDER_NAME}/'
    os.makedirs(AXONIUS_DEPLOYMENT_PATH, exist_ok=True)
    # Extracting source files from currently running python zip to AXONIUS_DEPLOYMENT_PATH
    # pylint: disable=protected-access
    for zip_path in zip_loader._files.keys():
        zip_path = zip_path.replace('\\', '/')
        if not zip_path.startswith(zip_folder_source_path):
            continue
        path = zip_path[len(zip_folder_source_path):]
        full_path = os.path.join(AXONIUS_DEPLOYMENT_PATH, path)
        if '/' in path:
            dir_name = os.path.dirname(full_path)
            if not os.path.isdir(dir_name):
                os.makedirs(dir_name)
        data = zip_loader.get_data(zip_path)
        open(full_path, 'wb').write(data)
        # chmod +x for .sh files
        if full_path.endswith('.sh') and sys.platform.startswith('linux'):
            os.chmod(full_path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC |
                     stat.S_IXGRP | stat.S_IXOTH | stat.S_IRGRP | stat.S_IROTH)

    push_old_instances_settings()


def install_requirements():
    print_state('Install requirements')
    pip3_path = os.path.join(VENV_PATH, 'bin', 'pip3')
    if sys.platform.startswith('win'):
        pip3_win_path = os.path.join(VENV_PATH, 'Scripts', 'pip3.exe')
        if os.path.exists(pip3_win_path):
            pip3_path = pip3_win_path
    requirements = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'requirements.txt')
    packages = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'deployment', 'packages')
    subprocess.check_call([pip3_path, '-V'])
    args = [pip3_path, 'install', '--upgrade', 'pip', '--find-links', packages,
            '--no-index',  # Don't use internet access
            '--no-cache']  # Don't use local cache
    subprocess.check_call(args)
    subprocess.check_call([pip3_path, '-V'])
    args = [pip3_path, 'install', '-r', requirements, '--find-links', packages,
            '--no-index',  # Don't use internet access
            '--no-cache']  # Don't use local cache
    subprocess.check_call(args)


def validate_old_state():
    if not os.path.isdir(AXONIUS_DEPLOYMENT_PATH):
        name = os.path.basename(AXONIUS_DEPLOYMENT_PATH)
        print(f'{name} folder wasn\'t found at {AXONIUS_DEPLOYMENT_PATH} (missing --first-time ?)')
        sys.exit(-1)
    else:
        chown_folder(AXONIUS_DEPLOYMENT_PATH)

    if not os.path.exists(WEAVE_PATH):
        name = os.path.basename(WEAVE_PATH)
        print(f'{name} binary wasn\'t found at {WEAVE_PATH}. please install weave and try again.')
        raise FileNotFoundError(f'{name} binary wasn\'t found at {WEAVE_PATH}')


def set_special_permissions():
    # Adding write permissions on .axonius_settings so node_maker can touch a new node.marker
    os.makedirs(AXONIUS_SETTINGS_PATH, exist_ok=True)
    cmd = f'chmod -R o+w {AXONIUS_SETTINGS_PATH}'
    run_cmd(cmd.split())

    # Adding write and execute permissions on all the scripts node_maker uses.
    for current_file in CHMOD_FILES:
        cmd = f'chmod +xr {current_file}'
        run_cmd(cmd.split())


def create_venv():
    print_state('Creating python venv')
    args = f'python3 -m virtualenv --python=python3.6 --clear {VENV_PATH} --never-download'.split(' ')
    subprocess.check_call(args)

    # running this script as executable because can't easily import in at this stage
    create_pth = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'devops', 'create_pth.py')
    subprocess.check_call(['python3', create_pth])


def install(first_time, no_research):
    if not first_time:
        validate_old_state()
        os.rename(AXONIUS_DEPLOYMENT_PATH, TEMPORAL_PATH)

    load_new_source()
    create_venv()
    install_requirements()

    print('Activating venv!')
    activate_this_file = os.path.join(VENV_PATH, 'bin', 'activate_this.py')
    # pylint: disable=exec-used
    exec(open(activate_this_file).read(), dict(__file__=activate_this_file))
    print('Venv activated!')
    # from this line on - we can use venv!

    from deployment.with_venv_install import after_venv_activation
    after_venv_activation(first_time, no_research)


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
