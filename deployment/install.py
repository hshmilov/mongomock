#!/usr/bin/env python3.6
"""
This script installs the system from scratch (using --first-time) or as an upgrade.
    * no parameters necessary...
    * it is intended to run as the __main__.py script for the final zip installer created by make.py
"""
import argparse
import datetime
import getpass
import os
import pwd
import shutil
import stat
import subprocess
import sys
import time
import zipfile

from utils import (AXONIUS_DEPLOYMENT_PATH, AXONIUS_OLD_ARCHIVE_PATH,
                   SOURCES_FOLDER_NAME, VENV_WRAPPER, AutoOutputFlush,
                   current_file_system_path, print_state)

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
RESTART_SYSTEM_ON_BOOT_CRON_SCRIPT_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCES_SCRIPT_PATH,
                                                       'restart_system_on_reboot.py')
INSTANCES_SETUP_SCRIPT_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCES_SCRIPT_PATH, 'setup_node.py')
INSTANCE_SETTINGS_DIR_NAME = '.axonius_settings'
INSTANCE_IS_MASTER_MARKER_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCE_SETTINGS_DIR_NAME, '.logged_in')
BOOTED_FOR_PRODUCTION_MARKER_PATH = os.path.join(
    AXONIUS_DEPLOYMENT_PATH, INSTANCE_SETTINGS_DIR_NAME, '.booted_for_production')
INSTANCE_CONNECT_USER_NAME = 'node_maker'
INSTANCE_CONNECT_USER_PASSWORD = 'M@ke1tRain'


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


def install(first_time, root_pass):
    if not first_time:
        validate_old_state(root_pass)
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

    setup_host()

    if not first_time:
        stop_old(keep_diag=True, keep_tunnel=True)

    load_images()

    start_axonius()
    set_logrotate(root_pass)

    if not first_time:
        archive_old_source()
        chown_folder(root_pass, TEMPORAL_PATH)
        set_booted_for_production()
        shutil.rmtree(TEMPORAL_PATH, ignore_errors=True)

    chown_folder(root_pass, AXONIUS_DEPLOYMENT_PATH)  # new sources


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


def setup_instances_user():
    try:
        pwd.getpwnam(INSTANCE_CONNECT_USER_NAME)
        print_state(f'{INSTANCE_CONNECT_USER_NAME} user exists')
    except KeyError:
        if not os.path.exists(INSTANCE_IS_MASTER_MARKER_PATH):
            print_state(f'Generating {INSTANCE_CONNECT_USER_NAME} user')
            for current_file in [INSTANCES_SETUP_SCRIPT_PATH, 'axonius.sh', 'prepare_python_env.sh']:
                subprocess.check_call(['chmod', '+xr', os.path.join(AXONIUS_DEPLOYMENT_PATH, current_file)])
            subprocess.check_call(['/usr/sbin/useradd', '-s',
                                   INSTANCES_SETUP_SCRIPT_PATH, '-G', 'docker,sudo', INSTANCE_CONNECT_USER_NAME])
            subprocess.check_call(
                f'usermod --password $(openssl passwd -1 {INSTANCE_CONNECT_USER_PASSWORD}) node_maker',
                shell=True)

            sudoers = open('/etc/sudoers', 'r').read()
            if INSTANCE_CONNECT_USER_NAME not in sudoers:
                subprocess.check_call(
                    f'echo "{INSTANCE_CONNECT_USER_NAME} ALL=(ALL) NOPASSWD: '
                    f'/usr/sbin/usermod" | EDITOR="tee -a" visudo',
                    shell=True)


def create_cronjob(script_path, cronjob_timing):
    print_state(f'Creating {script_path} cronjob')
    crontab_command = 'crontab -l | {{ cat; echo "{timing} /etc/cron.d/{script_name} > ' \
                      '/var/log/{log_name} 2>&1"; }} | crontab -'

    shutil.copyfile(script_path,
                    f'/etc/cron.d/{os.path.basename(script_path)}')
    subprocess.check_call(
        ['chown', 'root:root', f'/etc/cron.d/{os.path.basename(script_path)}'])
    subprocess.check_call(['chmod', '0700', f'/etc/cron.d/{os.path.basename(script_path)}'])
    try:
        cron_jobs = subprocess.check_output(['crontab', '-l']).decode('utf-8')
    except subprocess.CalledProcessError as exc:
        cron_jobs = ''

    if os.path.basename(script_path) not in cron_jobs:
        subprocess.check_call(crontab_command.format(timing=cronjob_timing, script_name=os.path.basename(script_path),
                                                     log_name=f'{os.path.basename(script_path).split(".")[0]}.log'),
                              shell=True)


def setup_instances_cronjobs():
    create_cronjob(DELETE_INSTANCES_USER_CRON_SCRIPT_PATH, '*/1 * * * *')
    create_cronjob(RESTART_SYSTEM_ON_BOOT_CRON_SCRIPT_PATH, '@reboot')


def push_old_instances_settings():
    print_state('Copying old settings (weave encryption key, master marker and first boot marker')
    if os.path.exists(os.path.join(TEMPORAL_PATH, INSTANCE_SETTINGS_DIR_NAME)):
        os.rename(os.path.join(TEMPORAL_PATH, INSTANCE_SETTINGS_DIR_NAME),
                  os.path.join(AXONIUS_DEPLOYMENT_PATH, INSTANCE_SETTINGS_DIR_NAME))


def setup_instances():
    # Save old weave pass:
    push_old_instances_settings()

    # Setup user
    setup_instances_user()

    # Setup cron-job
    setup_instances_cronjobs()


def setup_host():
    setup_instances()


def set_booted_for_production():
    open(BOOTED_FOR_PRODUCTION_MARKER_PATH, 'a').close()


def chown_folder(root_pass, path):
    cmd = f'chown -R ubuntu:ubuntu {path}'
    run_as_root(cmd.split(), root_pass)


def stop_old(keep_diag=True, keep_tunnel=True):
    print_state('Stopping old containers, and removing old <containers + images> [except diagnostics]')
    from destroy import destroy
    destroy(keep_diag=keep_diag, keep_tunnel=keep_tunnel)


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
        # pylint: disable=protected-access
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


def create_venv():
    print_state('Creating python venv')
    args = f'python3 -m virtualenv --python=python3 --clear {VENV_PATH} --never-download'.split(' ')
    subprocess.check_call(args)

    # running this script as executable because can't easily import in at this stage
    create_pth = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'devops', 'create_pth.py')
    subprocess.check_call(['python3', create_pth])


def run_as_root(args, passwd):
    sudo = f'sudo -S' if passwd != '' else 'sudo'
    print(' '.join(sudo.split() + args))
    proc = subprocess.Popen(sudo.split() + args, stdin=subprocess.PIPE)
    proc.communicate(passwd.encode() + b'\n')


def set_logrotate(root_pass):
    print_state('Setting logrotate on both docker logs and cortex logs')

    script = f'{DEPLOYMENT_FOLDER_PATH}/set_logrotate.py --cortex-path {AXONIUS_DEPLOYMENT_PATH}'
    cmd = f'{VENV_WRAPPER} {script}'
    run_as_root(cmd.split(), root_pass)


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
    from devops.axonius_system import main as system_main
    system_main('system up --all --prod'.split())
    print_state('System is up')

    print_state('Starting discovery')
    from devops.scripts import discover_now
    discover_now.main(should_wait=False)


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
