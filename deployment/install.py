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
from subprocess import CalledProcessError

from utils import AutoOutputFlush, AXONIUS_DEPLOYMENT_PATH, SOURCES_FOLDER_NAME, zip_loader, print_state, \
    current_file_system_path, safe_run_bash, AXONIUS_OLD_ARCHIVE_PATH

DEPLOYMENT_FOLDER_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'deployment')
DESTROY_SCRIPT_PATH = os.path.join(DEPLOYMENT_FOLDER_PATH, 'destroy.py')
VENV_WRAPPER = os.path.join(DEPLOYMENT_FOLDER_PATH, 'venv_wrapper.sh')
VENV_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'venv')
STATE_OUTPUT_PATH = os.path.join(os.path.dirname(current_file_system_path), 'encrypted.state')


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
    assert zip_loader is not None
    key, old_services, old_adapters = None, None, None
    if not just_install:
        validate_old_state()
        key, old_services, old_adapters = pre_install()
        if 'diagnostics' in old_services:
            old_services.remove('diagnostics')
        print(f'  Providers credentials file key: {key}')
        stop_old(True)
        archive_old_source()
        remove_old_source()
    load_images()
    load_new_source()
    create_venv()
    set_logrotate(root_pass)
    install_requirements()
    create_system(old_services, old_adapters)
    if key is not None:
        post_install(key)


def validate_old_state():
    """ Validates the presence of DESTROY_SCRIPT_PATH """
    if not os.path.isfile(DESTROY_SCRIPT_PATH):
        if not os.path.isdir(AXONIUS_DEPLOYMENT_PATH):
            name = os.path.basename(AXONIUS_DEPLOYMENT_PATH)
            raise Exception(f"{name} folder wasn't found at {AXONIUS_DEPLOYMENT_PATH} (missing --first-time ?)")
        raise Exception(f"destroy script wasn't found at {DESTROY_SCRIPT_PATH}")


def pre_install():
    print_state('Running pre install script')
    pre_script_path = os.path.join(DEPLOYMENT_FOLDER_PATH, 'pre_install.py')
    args = safe_run_bash([VENV_WRAPPER, pre_script_path, '--out', STATE_OUTPUT_PATH])
    ret = subprocess.run(args, stderr=subprocess.PIPE)
    if ret.returncode:
        stderr = ret.stderr.decode('utf-8')
        print(stderr)
        raise CalledProcessError(ret.returncode, args[0], stderr=stderr)
    key, old_services, old_adapters, _ = ret.stderr.decode('utf-8').split('\n')
    old_services = old_services.split('|')
    old_adapters = old_adapters.split('|')
    return key, old_services, old_adapters


def stop_old(keep_logs=False, keep_diag=True):
    print_state('Stopping old containers, and removing old <containers + volumes + images> [except diagnostics]')
    args = safe_run_bash([VENV_WRAPPER, DESTROY_SCRIPT_PATH])
    if keep_logs:
        args.append('--keep-logs')
    if keep_diag:
        args.append('--keep-diag')
    subprocess.check_call(args)


def archive_old_source():
    if sys.platform.startswith('win'):
        print_state(f'[SKIPPING] Archiving old source folder - not supported on windows')
        return
    archive_path = AXONIUS_OLD_ARCHIVE_PATH.format(datetime.datetime.now().strftime('%y%m%d-%H%M'))
    print_state(f'Archiving old source folder to: {archive_path}')
    subprocess.check_output(['tar', '-zcvf', archive_path, AXONIUS_DEPLOYMENT_PATH])


def remove_old_source():
    print_state('Removing old source folder')
    shutil.rmtree(AXONIUS_DEPLOYMENT_PATH, ignore_errors=True)


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
    print_state('Loading new source folder')
    zip_folder_source_path = f'{SOURCES_FOLDER_NAME}/'
    os.makedirs(AXONIUS_DEPLOYMENT_PATH)
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
    create_pth = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'devops', 'create_pth.py')
    subprocess.check_call(['python3', create_pth])


def set_logrotate(root_pass):
    print_state('Setting logrotate on both docker logs and cortex logs')
    args = safe_run_bash([VENV_WRAPPER, os.path.join(DEPLOYMENT_FOLDER_PATH, 'set_logrotate.py')])
    if root_pass is not None:
        args.extend(['--root-pass', root_pass])
    subprocess.check_call(args)


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


def create_system(old_services, old_adapters):
    print_state('Starting up axonius system')
    create_script_path = os.path.join(DEPLOYMENT_FOLDER_PATH, 'create.py')
    args = safe_run_bash([VENV_WRAPPER, create_script_path, '--prod'])
    if old_services is not None:
        args.extend(['--services'] + old_services)
    if old_adapters is not None:
        args.extend(['--adapters'] + old_adapters)
    subprocess.check_call(args)


def post_install(key):
    print_state('Running post install script')
    post_script_path = os.path.join(DEPLOYMENT_FOLDER_PATH, 'post_install.py')
    args = safe_run_bash([VENV_WRAPPER, post_script_path, '-f', STATE_OUTPUT_PATH, '--key', key])
    subprocess.check_call(args)


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
