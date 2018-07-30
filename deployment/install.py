#!/usr/bin/env python3
"""
This script installs the system from scratch (using --first-time) or as an upgrade.
    * no parameters necessary...
    * it is intended to run as the __main__.py script for the final zip installer created by make.py
"""
import argparse
import datetime
import os
import shutil
import subprocess
import stat
import sys
import time
import zipfile

from utils import AutoOutputFlush, AXONIUS_DEPLOYMENT_PATH, SOURCES_FOLDER_NAME, print_state, \
    current_file_system_path, AXONIUS_OLD_ARCHIVE_PATH

timestamp = datetime.datetime.now().strftime('%y%m%d-%H%M')

DEPLOYMENT_FOLDER_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'deployment')
VENV_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'venv')
STATE_OUTPUT_PATH = os.path.join(os.path.dirname(current_file_system_path), 'encrypted.state')
ARCHIVE_PATH = AXONIUS_OLD_ARCHIVE_PATH.format(timestamp)
TEMPORAL_PATH = f'{AXONIUS_DEPLOYMENT_PATH}_TEMP_{timestamp}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--first-time', action='store_true', default=False, help='First Time install')
    parser.add_argument('--root-pass', type=str, help='Root admin password', required=False, default=None)

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    start = time.time()
    install(args.first_time, args.root_pass)
    print_state(f'Done, took {int(time.time() - start)} seconds')


def install(just_install=False, root_pass=None):
    if not just_install:
        validate_old_state()
        os.rename(AXONIUS_DEPLOYMENT_PATH, TEMPORAL_PATH)

    load_new_source()
    create_venv()
    install_requirements()

    print('Activating venv!')
    activate_this_file = os.path.join(VENV_PATH, 'bin', 'activate_this.py')
    exec(open(activate_this_file).read(), dict(__file__=activate_this_file))
    print('Venv activated!')
    # from this line on - we can use venv!

    if not just_install:
        stop_old(keep_diag=True)

    load_images()

    set_logrotate(root_pass)
    start_axonius()

    if not just_install:
        archive_old_source()
        shutil.rmtree(TEMPORAL_PATH, ignore_errors=True)


def validate_old_state():
    if not os.path.isdir(AXONIUS_DEPLOYMENT_PATH):
        name = os.path.basename(AXONIUS_DEPLOYMENT_PATH)
        print(f"{name} folder wasn't found at {AXONIUS_DEPLOYMENT_PATH} (missing --first-time ?)")
        sys.exit(-1)


def stop_old(keep_diag=True):
    print_state('Stopping old containers, and removing old <containers + images> [except diagnostics]')
    from destroy import destroy
    destroy(keep_diag=keep_diag)


def archive_old_source():
    if sys.platform.startswith('win'):
        print_state(f'[SKIPPING] Archiving old source folder - not supported on windows')
        return

    print_state(f'Archiving old source folder to: {ARCHIVE_PATH}')
    subprocess.check_output(['tar', '-zcvf', ARCHIVE_PATH, TEMPORAL_PATH])


def load_images():
    print_state('Loading new images')
    # Using docker load from STDIN (input from images.tar inside currently running python zip)
    proc = subprocess.Popen(['docker', 'load'], stdin=subprocess.PIPE)
    with zipfile.ZipFile(current_file_system_path, 'r') as zip_file:
        zip_resource = zip_file.open('images.tar', 'r')
        state = 0
        size = zip_resource._left
        while True:
            current = zip_resource.read(4 * 1024 * 1024)
            state += len(current)
            if current == b'':
                break
            print(f'\r               \r  Reading {int(state * 100 / size)}%', end='')
            assert proc.stdin.write(current) == len(current)
        print('\r               \rReading - Done')
        proc.stdin.close()
        zip_resource.close()
    ret_code = proc.wait()
    if ret_code != 0:
        print(f'Docker load images return code: {ret_code}')
        raise Exception('Invalid return code from docker load command')


def load_new_source():
    from utils import zip_loader
    # this code run from _axonius.py zip, and assumes that zip loader exist
    assert zip_loader is not None

    print_state('Loading new source folder')
    zip_folder_source_path = f'{SOURCES_FOLDER_NAME}/'
    os.makedirs(AXONIUS_DEPLOYMENT_PATH, exist_ok=True)
    # Extracting source files from currently running python zip to AXONIUS_DEPLOYMENT_PATH
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


def create_venv():
    print_state('Creating python venv')
    args = f'python3 -m virtualenv --python=python3 --clear {VENV_PATH} --never-download'.split(' ')
    subprocess.check_call(args)

    # running this script as executable because can't easily import in at this stage
    create_pth = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'devops', 'create_pth.py')
    subprocess.check_call(['python3', create_pth])


def set_logrotate(root_pass):
    print_state('Setting logrotate on both docker logs and cortex logs')
    args = list()
    if root_pass is not None:
        args.extend(['--root-pass', root_pass])
    from set_logrotate import set_logrotate
    set_logrotate(args)


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


def start_axonius():
    print_state('Starting up axonius system')
    from devops.axonius_system import main
    main('system up --all --prod --exclude diagnostics'.split())
    print_state('System is up')


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
