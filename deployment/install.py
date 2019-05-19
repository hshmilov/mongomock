#!/usr/bin/env python3.6
"""
This script installs the system from scratch (using --first-time) or as an upgrade.
    * no parameters necessary...
    * it is intended to run as the __main__.py script for the final zip installer created by make.py
"""
import argparse
import datetime
import getpass
import json
import os
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
                   run_as_root,
                   chown_folder)

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
START_SYSTEM_ON_FIRST_BOOT_CRON_SCRIPT_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCES_SCRIPT_PATH,
                                                           'start_system_on_first_boot.py')
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
    parser.add_argument('--root-pass', action='store_true', default='', help='Sudo password')

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    start = time.time()
    root_pass = args.root_pass

    if root_pass == '' and os.geteuid() != 0:
        # we are not root, and don't have root password :(
        root_pass = getpass.getpass('sudo password: ')

    install(args.first_time, root_pass)
    print_state(f'Done, took {int(time.time() - start)} seconds')


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
            os.chmod(full_path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)


def install_requirements():
    print_state('Install requirements')
    pip3_path = os.path.join(VENV_PATH, 'bin', 'pip3')
    if sys.platform.startswith('win'):
        pip3_win_path = os.path.join(VENV_PATH, 'Scripts', 'pip3.exe')
        if os.path.exists(pip3_win_path):
            pip3_path = pip3_win_path
    requirements = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'requirements.txt')
    packages = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'deployment', 'packages')
    args = [pip3_path, 'install', '-r', requirements, '--find-links', packages,
            '--no-index',  # Don't use internet access
            '--no-cache']  # Don't use local cache
    subprocess.check_call(args)


def validate_old_state(root_pass):
    if not os.path.isdir(AXONIUS_DEPLOYMENT_PATH):
        name = os.path.basename(AXONIUS_DEPLOYMENT_PATH)
        print(f'{name} folder wasn\'t found at {AXONIUS_DEPLOYMENT_PATH} (missing --first-time ?)')
        sys.exit(-1)
    else:
        chown_folder(root_pass, AXONIUS_DEPLOYMENT_PATH)

    if not os.path.exists(WEAVE_PATH):
        name = os.path.basename(WEAVE_PATH)
        print(f'{name} binary wasn\'t found at {WEAVE_PATH}. please install weave and try again.')
        raise FileNotFoundError(f'{name} binary wasn\'t found at {WEAVE_PATH}')


def set_special_permissions(root_pass):
    # Adding write permissions on .axonius_settings so node_maker can touch a new node.marker
    os.makedirs(AXONIUS_SETTINGS_PATH, exist_ok=True)
    cmd = f'chmod -R o+w {AXONIUS_SETTINGS_PATH}'
    run_as_root(cmd.split(), root_pass)

    # Adding write and execute permissions on all the scripts node_maker uses.
    for current_file in CHMOD_FILES:
        cmd = f'chmod +xr {current_file}'
        run_as_root(cmd.split(), root_pass)


def create_venv():
    print_state('Creating python venv')
    args = f'python3 -m virtualenv --python=python3.6 --clear {VENV_PATH} --never-download'.split(' ')
    subprocess.check_call(args)

    # running this script as executable because can't easily import in at this stage
    create_pth = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'devops', 'create_pth.py')
    subprocess.check_call(['python3', create_pth])


def save_master_ip():
    # this is a transition code. after 2.5 we should have master ip stored everywhere

    # a stupid dependency chain forces to duplicate this string because we can't import at this stage
    # since this code can be removed after 2.5 it doesn't really matter
    master_key_path = Path('/home/ubuntu/cortex/.axonius_settings/__master')
    node_marker = Path('/home/ubuntu/cortex/.axonius_settings/connected_to_master.marker')

    if not node_marker.is_file():
        print(f'Not a node, skipping save master ip step')
        return

    if not master_key_path.is_file():
        try:
            report = subprocess.check_output('weave report'.split())
            report = json.loads(report)
            master_ip = report['Router']['Connections'][0]['Address'].split(':')[0]
            master_key_path.write_text(master_ip)
            print(f'saved master ip {master_ip} in {master_key_path}')

        except Exception as e:
            print(f'failed to save master ip {e}')
    else:
        print(f'master ip was present at {master_key_path}')


def install(first_time, root_pass):
    if not first_time:
        validate_old_state(root_pass)
        save_master_ip()  # before we destroy weave net - backup the master ip. can remove after 2.5
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
    after_venv_activation(first_time, root_pass)


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
