import json
import os
import pwd
import shutil
import subprocess
import zipfile

from axonius.consts.system_consts import PYRUN_PATH_HOST
from axonius.utils.network.docker_network import read_weave_network_range
from conf_tools import get_customer_conf_json
from install import (TEMPORAL_PATH,
                     AXONIUS_SETTINGS_PATH,
                     INSTANCE_CONNECT_USER_NAME,
                     INSTANCE_IS_MASTER_MARKER_PATH,
                     INSTANCES_SETUP_SCRIPT_PATH,
                     INSTANCE_CONNECT_USER_PASSWORD,
                     DELETE_INSTANCES_USER_CRON_SCRIPT_PATH,
                     SYSTEM_BOOT_CRON_SCRIPT_PATH,
                     INSTANCE_SETTINGS_DIR_NAME,
                     BOOTED_FOR_PRODUCTION_MARKER_PATH,
                     DEPLOYMENT_FOLDER_PATH,
                     chown_folder,
                     set_special_permissions)
from lists import OLD_CRONJOBS
from scripts.host_installation.watchdog_cron import WATCHDOG_CRON_SCRIPT_PATH
from scripts.instances.network_utils import get_weave_subnet_ip_range
from sysctl_editor import set_sysctl_value
from utils import AXONIUS_DEPLOYMENT_PATH, print_state, current_file_system_path, VENV_WRAPPER, run_as_root


def after_venv_activation(first_time, root_pass):
    print(f'installing on top of customer_conf: {get_customer_conf_json()}')
    if not first_time:
        stop_old(keep_diag=True, keep_tunnel=True)
    setup_host()
    load_images()
    set_logrotate(root_pass)
    if not first_time:
        chown_folder(root_pass, TEMPORAL_PATH)
        os.makedirs(AXONIUS_SETTINGS_PATH, exist_ok=True)
        set_booted_for_production()
    set_special_permissions(root_pass)
    # chown before start Axonius which tends to be the failure point in bad updates.
    chown_folder(root_pass, AXONIUS_DEPLOYMENT_PATH)
    # This parts tends to have problems. Minimize the code after it as much as possible.
    if not first_time:
        start_axonius()
        run_discovery()

        # Chown again after the run, to make log file which are created afterwards be also part of it
        set_special_permissions(root_pass)
        chown_folder(root_pass, AXONIUS_DEPLOYMENT_PATH)

        shutil.rmtree(TEMPORAL_PATH, ignore_errors=True)


def reset_weave_network_on_bad_ip_allocation():
    try:
        weave_netrowk_range = read_weave_network_range()
        if weave_netrowk_range != get_weave_subnet_ip_range():
            print('Resetting weave network.')
            subprocess.check_call('weave reset'.split())
        else:
            print('Weave subnet range is configured correctly - Skipping reset.')
    except subprocess.CalledProcessError:
        print('Weave operation failed - Skipping reset.')
    except json.JSONDecodeError:
        print('Failed to decode weave report - Skipping reset.')


def remove_old_network():
    # Will remove old bridged docker network if it exists to make sure we avoid an IP collision.
    subprocess.call('docker network rm axonius'.split())


def reset_network():
    remove_old_network()
    reset_weave_network_on_bad_ip_allocation()


def setup_instances_user():
    try:
        pwd.getpwnam(INSTANCE_CONNECT_USER_NAME)
        print_state(f'{INSTANCE_CONNECT_USER_NAME} user exists')
    except KeyError:
        if not os.path.exists(INSTANCE_IS_MASTER_MARKER_PATH):
            print_state(f'Generating {INSTANCE_CONNECT_USER_NAME} user')
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


def create_cronjob(script_path, cronjob_timing, specific_run_env='', keep_script_location=False):
    print_state(f'Creating {script_path} cronjob')
    if keep_script_location:
        crontab_command = 'crontab -l | {{ cat; echo "{timing} {specific_run_env}{script_name} > ' \
                          '/var/log/{log_name} 2>&1"; }} | crontab -'
    else:
        crontab_command = 'crontab -l | {{ cat; echo "{timing} {specific_run_env}/etc/cron.d/{script_name} > ' \
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

    if specific_run_env != '':
        specific_run_env += ' '

    script_path = os.path.basename(script_path) if not keep_script_location else script_path

    if os.path.basename(script_path) not in cron_jobs:
        subprocess.check_call(crontab_command.format(timing=cronjob_timing, script_name=script_path,
                                                     log_name=f'{os.path.basename(script_path).split(".")[0]}.log',
                                                     specific_run_env=specific_run_env),
                              shell=True)


def cleanup_old_cronjobs():
    for cronjob_name in OLD_CRONJOBS:
        remove_cronjob(cronjob_name)


def setup_instances_cronjobs():
    cleanup_old_cronjobs()
    create_cronjob(DELETE_INSTANCES_USER_CRON_SCRIPT_PATH, '*/1 * * * *', specific_run_env='/usr/local/bin/python3')
    create_cronjob(SYSTEM_BOOT_CRON_SCRIPT_PATH, '@reboot', keep_script_location=True)


def remove_cronjob(cronjob_name):
    remove_cron_command = 'crontab -l | grep -v \'{cronjob_name}\' | crontab -'
    subprocess.check_call(remove_cron_command.format(cronjob_name=cronjob_name), shell=True)


def create_system_cronjobs():
    remove_cronjob(WATCHDOG_CRON_SCRIPT_PATH)
    create_cronjob(script_path=WATCHDOG_CRON_SCRIPT_PATH,
                   cronjob_timing='*/15 * * * *',
                   specific_run_env=str(PYRUN_PATH_HOST),
                   keep_script_location=True)


def push_old_instances_settings():
    print_state('Copying old settings (weave encryption key, master marker and first boot marker')
    if os.path.exists(os.path.join(TEMPORAL_PATH, INSTANCE_SETTINGS_DIR_NAME)):
        os.rename(os.path.join(TEMPORAL_PATH, INSTANCE_SETTINGS_DIR_NAME),
                  AXONIUS_SETTINGS_PATH)


def setup_instances():
    # Save old weave pass:
    push_old_instances_settings()

    # Setup user
    setup_instances_user()

    # Setup cron-job
    setup_instances_cronjobs()


def setup_host():
    setup_instances()
    reset_network()
    create_system_cronjobs()
    set_sysctl_value('kernel.pid_max', '64000')
    os.system('sysctl --load')


def set_booted_for_production():
    open(BOOTED_FOR_PRODUCTION_MARKER_PATH, 'a').close()


def stop_old(keep_diag=True, keep_tunnel=True):
    print_state('Stopping old containers, and removing old <containers + images> [except diagnostics]')
    from destroy import destroy
    destroy(keep_diag=keep_diag, keep_tunnel=keep_tunnel)


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


def set_logrotate(root_pass):
    print_state('Setting logrotate on both docker logs and cortex logs')

    script = f'{DEPLOYMENT_FOLDER_PATH}/set_logrotate.py --cortex-path {AXONIUS_DEPLOYMENT_PATH}'
    cmd = f'{VENV_WRAPPER} {script}'
    run_as_root(cmd.split(), root_pass)


def run_discovery():
    print_state('Starting discovery')
    from devops.scripts import discover_now
    # This will skip on a node (since there's no system-scheduler to run a discovery).
    discover_now.main(should_wait=False)


def start_axonius():
    print_state('Starting up axonius system')
    from devops.axonius_system import main as system_main
    system_main('system up --all --prod --restart'.split())
    print_state('System is up')
