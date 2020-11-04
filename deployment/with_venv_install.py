import json
import os
import pwd
import shutil
import subprocess

from retrying import retry


from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, MONGO_UNIQUE_NAME
from axonius.consts.system_consts import NODE_MARKER_PATH
from conf_tools import get_customer_conf_json
from install import (TEMPORAL_PATH,
                     AXONIUS_SETTINGS_PATH,
                     DELETE_INSTANCES_USER_CRON_SCRIPT_PATH,
                     SYSTEM_BOOT_CRON_SCRIPT_PATH,
                     BOOTED_FOR_PRODUCTION_MARKER_PATH,
                     DEPLOYMENT_FOLDER_PATH,
                     set_special_permissions)
from install_utils import CRON_D_PATH, create_cronjob, stop_old
from lists import OLD_CRONJOBS
from scripts.host_installation.watchdog_cron import WATCHDOG_CRON_SCRIPT_PATH
from scripts.instances.instances_consts import NOLOGINER_USER_NAME
from scripts.instances.instances_modes import get_instance_mode, InstancesModes
from scripts.instances.network_utils import connect_axonius_manager_to_weave
from scripts.maintenance_tools.cluster_reader import read_cluster_data
from scripts.maintenance_tools.cluster_upgrader import shutdown_adapters, download_upgrader_on_nodes, upgrade_nodes
from services.plugins.httpd_service import HttpdService
from services.standalone_services.node_proxy_service import NodeProxyService
from services.standalone_services.tunneler_service import TunnelerService
from services.weave_service import is_weave_up
from utils import (AXONIUS_DEPLOYMENT_PATH,
                   print_state,
                   run_cmd)


def after_venv_activation(first_time, no_research, master_only, installer_path):
    print(f'installing on top of customer_conf: {get_customer_conf_json()}')
    node_instances = None
    # If this is a master and it should upgrade the entire master
    if not first_time and not NODE_MARKER_PATH.is_file() and not master_only:
        print_state('Upgrading entire cluster')
        if is_weave_up():
            connect_axonius_manager_to_weave()
        cluster_data = read_cluster_data()
        if cluster_data:
            node_instances = [instance for instance in cluster_data['instances']
                              if instance['node_id'] != cluster_data['my_entity']['node_id']]
            print_state('Shutting down adapters on nodes')
            shutdown_adapters(node_instances)
            # if we use remote mongo, upgrade the mongo node before master
            if get_instance_mode() == InstancesModes.remote_mongo.value:
                print_state('Downloading upgrader on remote mongo node')
                remote_mongo_node_id = find_mongo_instance(node_instances)
                print_state(f'remote mongo node id: {remote_mongo_node_id.get("node_id")}')
                print_state('Upgrading remote mongo node')
                httpd_service = HttpdService()
                httpd_service.take_process_ownership()
                httpd_service.start(allow_restart=True, show_print=False, mode='prod')
                download_upgrader_on_nodes([remote_mongo_node_id, ])
                upgrade_nodes(node_instances)
                node_instances = [node for node in node_instances
                                  if node.get('node_id') != remote_mongo_node_id.get('node_id')]

    if not first_time:
        stop_old()

    if not first_time:
        os.makedirs(AXONIUS_SETTINGS_PATH, exist_ok=True)
        set_booted_for_production()
    set_special_permissions()
    # This parts tends to have problems. Minimize the code after it as much as possible.
    if not first_time:
        start_axonius()
        if no_research is False:
            run_discovery()

        # Chown again after the run, to make log file which are created afterwards be also part of it
        set_special_permissions()

        shutil.rmtree(TEMPORAL_PATH, ignore_errors=True)

    if not first_time and not NODE_MARKER_PATH.is_file() and not master_only and node_instances:
        print_state('Downloading upgrader on nodes')
        download_upgrader_on_nodes(node_instances)
        print_state('Upgrading nodes')
        upgrade_nodes(node_instances)


@retry(stop_max_attempt_number=3, wait_fixed=1000)
def find_mongo_instance(node_instances):
    try:
        report = subprocess.check_output(f'/usr/local/bin/weave report'.split())
        report = json.loads(report)
        # get master instance mac address
        master_mac = report['Router']['Peers'][0]['Name']
        dns_entries = report['DNS']['Entries']
        # list weave dns entries
        # weave have 2 dns records for mongo, one for the master proxy and one for the real mongo
        mongo_instance = [x for x in dns_entries
                          if x['Hostname'].startswith(MONGO_UNIQUE_NAME) and master_mac not in x['Origin']][0]
        remote_mongo_instance_control_instance = \
            [x for x in dns_entries if x['Hostname'].startswith('instance_control') and
             mongo_instance['Origin'] == x['Origin']][0]
        for node in node_instances:
            if remote_mongo_instance_control_instance.get('Hostname', '').startswith(node.get(PLUGIN_UNIQUE_NAME)):
                return node
        return None
    except Exception:
        print('Error while finding remote mongo instance')
        raise


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
                   specific_run_env='/usr/local/bin/python3',
                   keep_script_location=True)

    sched_prov_cron = 'chef_scheduled_provision'
    remove_cronjob(sched_prov_cron)
    create_cronjob(script_path=f'{CRON_D_PATH}/{sched_prov_cron}.sh',
                   cronjob_timing='*/1 * * * *', keep_script_location=True)


def setup_nologin_user():
    try:
        pwd.getpwnam(NOLOGINER_USER_NAME)
        print_state(f'{NOLOGINER_USER_NAME} user exists')
    except KeyError:
        subprocess.check_call(['/usr/sbin/useradd', '-s', '/bin/false', '-d', '/tmp/', NOLOGINER_USER_NAME])
        # create the user


def set_booted_for_production():
    open(BOOTED_FOR_PRODUCTION_MARKER_PATH, 'a').close()


def set_logrotate():
    print_state('Setting logrotate on both docker logs and cortex logs')

    script = f'python3 {DEPLOYMENT_FOLDER_PATH}/set_logrotate.py --cortex-path {AXONIUS_DEPLOYMENT_PATH}'
    run_cmd(script.split())


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
