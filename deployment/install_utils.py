import grp
import json
import os
import pwd
import shutil
import subprocess
from pathlib import Path

from conf_tools import get_customer_conf_json
from install import INSTANCE_IS_MASTER_MARKER_PATH, INSTANCES_SETUP_SCRIPT_PATH, INSTANCE_CONNECT_USER_PASSWORD, \
    DELETE_INSTANCES_USER_CRON_SCRIPT_PATH, SYSTEM_BOOT_CRON_SCRIPT_PATH, DEPLOYMENT_FOLDER_PATH
from lists import OLD_CRONJOBS
from scripts.host_installation.watchdog_cron import WATCHDOG_CRON_SCRIPT_PATH
from scripts.instances.instances_consts import INSTANCE_CONNECT_USER_NAME, NOLOGINER_USER_NAME, WEAVE_NETWORK_SUBNET_KEY
from sysctl_editor import get_sysctl_value, set_sysctl_value
from utils import print_state, AXONIUS_DEPLOYMENT_PATH, RESOURCES_PATH, run_cmd
DEFAULT_WEAVE_SUBNET_IP_RANGE = '171.17.0.0/16'

HOST_TASKS_SCRIPT_PATH = '/home/ubuntu/cortex/devops/scripts/watchdog/restart_host_tasks.sh'
CRON_D_PATH = Path('/etc/cron.d')
SOMAXCONN = 20000


def copy_file(local_path, dest_path, mode=0o700, user='root', group='root'):
    local_path = Path(local_path)
    dest_path = Path(dest_path)
    print(f'placing {local_path} in {dest_path} as {oct(mode)} {user}:{group}')
    shutil.copyfile(local_path, dest_path)
    dest_path.chmod(mode)
    shutil.chown(dest_path, user=user, group=group)


def read_weave_network_range():
    report = subprocess.check_output(f'/usr/local/bin/weave report'.split())
    report = json.loads(report)
    weave_netrowk_range = report['IPAM']['Range']
    return weave_netrowk_range


def get_weave_subnet_ip_range():
    conf = get_customer_conf_json()

    weave_subnet = conf.get(WEAVE_NETWORK_SUBNET_KEY, DEFAULT_WEAVE_SUBNET_IP_RANGE)

    if WEAVE_NETWORK_SUBNET_KEY in conf:
        print(f'Found custom weave network ip range: {weave_subnet}')
    else:
        print(f'Using default weave ip range {weave_subnet}')

    return weave_subnet


def remove_old_network():
    # Will remove old bridged docker network if it exists to make sure we avoid an IP collision.
    subprocess.call('docker network rm axonius'.split())


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
            all_groups = [x.gr_name for x in grp.getgrall()]
            sudoers_group_name = 'sudo' if 'sudo' in all_groups else 'wheel'

            subprocess.check_call(
                ['/usr/sbin/useradd', '-s', INSTANCES_SETUP_SCRIPT_PATH, '-d', AXONIUS_DEPLOYMENT_PATH, '-G',
                 f'docker,{sudoers_group_name}', INSTANCE_CONNECT_USER_NAME])
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
                subprocess.check_call(
                    f'echo "{INSTANCE_CONNECT_USER_NAME} ALL=(ALL) NOPASSWD: '
                    f'/usr/sbin/useradd" | EDITOR="tee -a" visudo',
                    shell=True)
                # For the creation of the tunneler log dir on first run.
                subprocess.check_call(
                    f'echo "{INSTANCE_CONNECT_USER_NAME} ALL=(ALL) NOPASSWD: '
                    f'/bin/mkdir" | EDITOR="tee -a" visudo',
                    shell=True)


def setup_nologin_user():
    try:
        pwd.getpwnam(NOLOGINER_USER_NAME)
        print_state(f'{NOLOGINER_USER_NAME} user exists')
    except KeyError:
        subprocess.check_call(['/usr/sbin/useradd', '-s', '/bin/false', '-d', '/tmp/', NOLOGINER_USER_NAME])
        # create the user


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


def remove_cronjob(cronjob_name):
    remove_cron_command = 'crontab -l | grep -v \'{cronjob_name}\' | crontab -'
    subprocess.check_call(remove_cron_command.format(cronjob_name=cronjob_name), shell=True)


def cleanup_old_cronjobs():
    for cronjob_name in OLD_CRONJOBS:
        remove_cronjob(cronjob_name)


def setup_instances_cronjobs():
    cleanup_old_cronjobs()
    create_cronjob(DELETE_INSTANCES_USER_CRON_SCRIPT_PATH, '*/1 * * * *', specific_run_env='/usr/local/bin/python3')
    create_cronjob(SYSTEM_BOOT_CRON_SCRIPT_PATH, '@reboot', keep_script_location=True)


def setup_instances():
    # Setup user
    setup_instances_user()

    setup_nologin_user()

    # Setup cron-job
    setup_instances_cronjobs()

    resources_as_path = Path(RESOURCES_PATH)
    copy_file(resources_as_path / 'weave-2.7.0', '/usr/local/bin/weave', mode=0o755, user='root', group='root')
    Path('/etc/sudoers.d/90-ubuntu').write_text('ubuntu ALL=(ALL) NOPASSWD: ALL\n')
    Path('/etc/sudoers.d/90-ubuntu').chmod(mode=440)


def create_system_cronjobs():
    remove_cronjob(WATCHDOG_CRON_SCRIPT_PATH)
    create_cronjob(script_path=WATCHDOG_CRON_SCRIPT_PATH,
                   cronjob_timing='*/15 * * * *',
                   specific_run_env='/usr/local/bin/python3',
                   keep_script_location=True)

    remove_cronjob(HOST_TASKS_SCRIPT_PATH)
    create_cronjob(script_path=HOST_TASKS_SCRIPT_PATH,
                   cronjob_timing='*/15 * * * *',
                   specific_run_env='/bin/bash',
                   keep_script_location=True)

    sched_prov_cron = 'chef_scheduled_provision'
    remove_cronjob(sched_prov_cron)
    create_cronjob(script_path=f'{CRON_D_PATH}/{sched_prov_cron}.sh',
                   cronjob_timing='*/1 * * * *', keep_script_location=True)


def setup_host():
    reset_network()
    setup_instances()
    create_system_cronjobs()
    set_sysctl_value('kernel.pid_max', '64000')
    set_sysctl_value('kernel.threads-max', '200000')
    set_sysctl_value('kernel.panic', '10')
    set_sysctl_value('net.ipv4.conf.all.accept_redirects', '0')
    set_sysctl_value('net.ipv4.conf.default.accept_redirects', '0')
    set_sysctl_value('net.ipv4.conf.all.secure_redirects', '0')
    set_sysctl_value('net.ipv4.conf.default.secure_redirects', '0')
    set_sysctl_value('net.ipv4.conf.all.forwarding', '1')
    try:
        if int(get_sysctl_value('net.core.somaxconn', '-1')) < SOMAXCONN:
            set_sysctl_value('net.core.somaxconn', str(SOMAXCONN))
    except Exception as e:
        print(f'Couldn\'t get/set the value of net.core.somaxconn: {str(e)}')
    os.system('sysctl --load')

    for user in ['ubuntu', 'customer']:
        try:
            try:
                with open(f'/home/{user}/.bash_aliases', 'rt') as f:
                    content = f.read().splitlines()
            except FileNotFoundError:
                content = []

            alias_line = 'alias axenv="source /home/ubuntu/cortex/ax_env.sh"'

            for i, line in enumerate(content):
                if line.startswith('alias axenv'):
                    content[i] = alias_line
                    break
            else:
                content.append(alias_line)

            with open(f'/home/{user}/.bash_aliases', 'wt') as f:
                f.write('\n'.join(content))

            shutil.chown(f'/home/{user}/.bash_aliases', user=user, group=user)
        except Exception as e:
            print(f'Could not install bash_aliases for user {user}: {str(e)}')


def load_images():
    print_state('Loading new images')
    subprocess.check_call(['docker', 'load', '-i', 'images.tar'])


def launch_axonius_manager():
    os.system(f'/bin/sh -c "cd {AXONIUS_DEPLOYMENT_PATH}; ./run_axonius_manager.sh"')


def restart_host_tasks():
    os.system(f'/bin/sh -c "cd {AXONIUS_DEPLOYMENT_PATH}/devops/scripts/watchdog; ./restart_host_tasks.sh"')


def stop_old():
    print_state('Stopping old containers, and removing old <containers + images> [except diagnostics]')
    from destroy import destroy
    destroy()
    # We load the second time after the deletion of all the other images
    load_images()


def set_logrotate():
    print_state('Setting logrotate on both docker logs and cortex logs')

    script = f'python3 {DEPLOYMENT_FOLDER_PATH}/set_logrotate.py --cortex-path {AXONIUS_DEPLOYMENT_PATH}'
    run_cmd(script.split())
