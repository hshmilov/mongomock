import json
import os
import pwd
import shutil
import subprocess
import zipfile
from pathlib import Path

import distro

from axonius.consts.system_consts import PYRUN_PATH_HOST, NODE_MARKER_PATH
from axonius.utils.network.docker_network import read_weave_network_range
from conf_tools import get_customer_conf_json
from install import (TEMPORAL_PATH,
                     AXONIUS_SETTINGS_PATH,
                     INSTANCE_IS_MASTER_MARKER_PATH,
                     INSTANCES_SETUP_SCRIPT_PATH,
                     INSTANCE_CONNECT_USER_PASSWORD,
                     DELETE_INSTANCES_USER_CRON_SCRIPT_PATH,
                     SYSTEM_BOOT_CRON_SCRIPT_PATH,
                     BOOTED_FOR_PRODUCTION_MARKER_PATH,
                     DEPLOYMENT_FOLDER_PATH,
                     chown_folder,
                     set_special_permissions)
from lists import OLD_CRONJOBS
from scripts.host_installation.watchdog_cron import WATCHDOG_CRON_SCRIPT_PATH
from scripts.instances.instances_consts import INSTANCE_CONNECT_USER_NAME
from scripts.instances.network_utils import get_weave_subnet_ip_range
from scripts.maintenance_tools.cluster_reader import read_cluster_data
from scripts.maintenance_tools.cluster_upgrader import shutdown_adapters, download_upgrader_on_nodes, upgrade_nodes
from services.standalone_services.node_proxy_service import NodeProxyService
from services.standalone_services.tunneler_service import TunnelerService
from sysctl_editor import set_sysctl_value
from utils import (AXONIUS_DEPLOYMENT_PATH,
                   print_state,
                   current_file_system_path,
                   VENV_WRAPPER,
                   run_cmd,
                   RESOURCES_PATH)

CRON_D_PATH = Path('/etc/cron.d')


def copy_file(local_path, dest_path, mode=0o700, user='root', group='root'):
    local_path = Path(local_path)
    dest_path = Path(dest_path)
    print(f'placing {local_path} in {dest_path} as {oct(mode)} {user}:{group}')
    shutil.copyfile(local_path, dest_path)
    dest_path.chmod(mode)
    shutil.chown(dest_path, user=user, group=group)


def after_venv_activation(first_time, no_research, master_only, installer_path):
    print(f'installing on top of customer_conf: {get_customer_conf_json()}')
    node_instances = None

    # If this is a master and it should upgrade the entire master
    if not NODE_MARKER_PATH.is_file() and not master_only:
        print_state('Upgrading entire cluster')
        cluster_data = read_cluster_data()
        node_instances = [instance for instance in cluster_data['instances']
                          if instance['node_id'] != cluster_data['my_entity']['node_id']]
        print_state('Shutting down adapters on nodes')
        shutdown_adapters(node_instances)

    if not first_time:
        stop_old()

    setup_host()
    load_images()
    set_logrotate()
    if not first_time:
        chown_folder(TEMPORAL_PATH)
        os.makedirs(AXONIUS_SETTINGS_PATH, exist_ok=True)
        set_booted_for_production()
    set_special_permissions()
    # chown before start Axonius which tends to be the failure point in bad updates.
    chown_folder(AXONIUS_DEPLOYMENT_PATH)
    # This parts tends to have problems. Minimize the code after it as much as possible.
    if not first_time:
        start_axonius()
        if no_research is False:
            run_discovery()

        # Chown again after the run, to make log file which are created afterwards be also part of it
        set_special_permissions()
        chown_folder(AXONIUS_DEPLOYMENT_PATH)

        shutil.rmtree(TEMPORAL_PATH, ignore_errors=True)

    if not NODE_MARKER_PATH.is_file() and not master_only:
        print_state('Downloading upgrader on nodes')
        download_upgrader_on_nodes(node_instances, installer_path)
        print_state('Upgrading nodes')
        upgrade_nodes(node_instances)


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
            # sudo group doesn't exist in centos and rhel the equivalent is named wheel.
            sudoers_group_name = 'wheel' if any([word in distro.linux_distribution(
                full_distribution_name=False) for word in ['centos', 'rhel']]) else 'sudo'

            subprocess.check_call(['/usr/sbin/useradd', '-s',
                                   INSTANCES_SETUP_SCRIPT_PATH, '-G', f'docker,{sudoers_group_name}',
                                   INSTANCE_CONNECT_USER_NAME])
            subprocess.check_call(
                f'usermod --password $(openssl passwd -1 {INSTANCE_CONNECT_USER_PASSWORD}) node_maker',
                shell=True)

            sudoers = open('/etc/sudoers', 'r').read()
            if INSTANCE_CONNECT_USER_NAME not in sudoers:
                # To change the node_maker password after connection.
                subprocess.check_call(
                    f'echo "{INSTANCE_CONNECT_USER_NAME} ALL=(ALL) NOPASSWD: '
                    f'/usr/sbin/usermod" | EDITOR="tee -a" visudo',
                    shell=True)
                # To run the system as ubuntu.
                subprocess.check_call(
                    f'echo "{INSTANCE_CONNECT_USER_NAME} ALL=(ALL) NOPASSWD: '
                    f'/sbin/runuser" | EDITOR="tee -a" visudo',
                    shell=True)
                # For the creation of the tunneler log dir on first run.
                subprocess.check_call(
                    f'echo "{INSTANCE_CONNECT_USER_NAME} ALL=(ALL) NOPASSWD: '
                    f'/bin/mkdir" | EDITOR="tee -a" visudo',
                    shell=True)


def create_cronjob(script_path, cronjob_timing, specific_run_env='', keep_script_location=False):
    print_state(f'Creating {script_path} cronjob')
    if keep_script_location:
        crontab_command = 'crontab -l | {{ cat; echo "{timing} {specific_run_env}{script_name} >> ' \
                          '/var/log/{log_name} 2>&1"; }} | crontab -'
    else:
        crontab_command = 'crontab -l | {{ cat; echo "{timing} {specific_run_env}' \
                          + str(CRON_D_PATH) + '/{script_name} >> /var/log/{log_name} 2>&1"; }} | crontab -'

        copy_file(script_path, CRON_D_PATH / os.path.basename(script_path))

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
                                                     specific_run_env=specific_run_env), shell=True)


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

    sched_prov_cron = 'chef_scheduled_provision'
    remove_cronjob(sched_prov_cron)
    create_cronjob(script_path=f'{CRON_D_PATH}/{sched_prov_cron}.sh',
                   cronjob_timing='*/1 * * * *', keep_script_location=True)


def setup_instances():
    # Setup user
    setup_instances_user()

    # Setup cron-job
    setup_instances_cronjobs()

    resources_as_path = Path(RESOURCES_PATH)
    copy_file(resources_as_path / 'weave-2.6.0', '/usr/local/bin/weave', mode=0o755, user='root', group='root')
    Path('/etc/sudoers.d/90-ubuntu').write_text('ubuntu ALL=(ALL) NOPASSWD: ALL\n')
    Path('/etc/sudoers.d/90-ubuntu').chmod(mode=440)


def setup_host():
    setup_instances()
    reset_network()
    create_system_cronjobs()
    set_sysctl_value('kernel.pid_max', '64000')
    set_sysctl_value('kernel.threads-max', '200000')
    set_sysctl_value('kernel.panic', '10')
    set_sysctl_value('net.ipv4.conf.all.accept_redirects', '0')
    set_sysctl_value('net.ipv4.conf.default.accept_redirects', '0')
    set_sysctl_value('net.ipv4.conf.all.secure_redirects', '0')
    set_sysctl_value('net.ipv4.conf.default.secure_redirects', '0')
    os.system('sysctl --load')


def set_booted_for_production():
    open(BOOTED_FOR_PRODUCTION_MARKER_PATH, 'a').close()


def stop_old():
    print_state('Stopping old containers, and removing old <containers + images> [except diagnostics]')
    from destroy import destroy
    destroy()


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


def set_logrotate():
    print_state('Setting logrotate on both docker logs and cortex logs')

    script = f'{DEPLOYMENT_FOLDER_PATH}/set_logrotate.py --cortex-path {AXONIUS_DEPLOYMENT_PATH}'
    cmd = f'{VENV_WRAPPER} {script}'
    run_cmd(cmd.split())


def run_discovery():
    print_state('Starting discovery')
    from devops.scripts import discover_now
    # This will skip on a node (since there's no system-scheduler to run a discovery).
    discover_now.main(should_wait=False)


def run_tunnels():
    tun = TunnelerService()
    tun.take_process_ownership()
    tun.start(mode='prod', allow_restart=True, show_print=False)
    proxy = NodeProxyService()
    proxy.take_process_ownership()
    proxy.start(mode='prod', allow_restart=True, show_print=False)


def start_axonius():
    print_state('Starting up axonius system')
    from devops.axonius_system import main as system_main
    system_main('system up --all --prod --restart'.split())
    if NODE_MARKER_PATH.is_file():
        run_tunnels()
    print_state('System is up')
