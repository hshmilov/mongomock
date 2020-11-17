#!/usr/bin/env python3

import json
import subprocess
import shlex
import argparse
from pathlib import Path
import shutil

import requests
from pymongo import MongoClient

from axonius.consts.instance_control_consts import InstanceControlConsts
from axonius.consts.system_consts import NODE_MARKER_PATH, DOCKERHUB_URL
from scripts.instances.network_utils import weave_dns_lookup
from scripts.maintenance_tools.cluster_reader import read_cluster_data
from services.plugin_service import API_KEY_HEADER

REQUEST_TIMEOUT = 60 * 30


def request_instance_control(plugin_unique_name, endpoint):
    plugin_unique_name_ip = weave_dns_lookup(plugin_unique_name)
    if not plugin_unique_name_ip:
        print(f'Error while resolving {plugin_unique_name}')
    res = requests.get(f'https://{plugin_unique_name_ip}:443/api/{endpoint}', verify=False,
                       timeout=REQUEST_TIMEOUT)
    print(res.text.strip())
    assert res.status_code == 200


def update_instances_upgrade_script(instances):
    client = MongoClient(
        'mongo.axonius.local', retryWrites=True,
        username='ax_user', password='ax_pass',
        localthresholdms=1000, connect=False
    )
    some_config = client['core']['configs'].find_one({})
    for instance in instances:
        plugin_unique_name_ip = weave_dns_lookup(instance['plugin_unique_name'])
        res = requests.post(f'https://{plugin_unique_name_ip}:443/api/trigger/execute_shell?blocking=False',
                            verify=False,
                            headers={API_KEY_HEADER: some_config['api_key'],
                                     'x-plugin-name': some_config['plugin_name'],
                                     'x-unique-plugin-name': some_config['plugin_unique_name']},
                            json={'cmd': 'sed -i s/python3/sh/g '
                                         '/home/ubuntu/cortex/devops/scripts/instances/run_upgrade_on_instance.sh'})
        print(res.text.strip())
        assert res.status_code == 200


def run_upgrade_phase_on_node(node, phase):
    node_id = node['node_id']
    instance_control_name = node['plugin_unique_name']
    print(f'Starting phase {phase} on node {node_id} ({instance_control_name})')
    request_instance_control(instance_control_name, phase)


def shutdown_adapters(instances):
    for node in instances:
        run_upgrade_phase_on_node(node, InstanceControlConsts.EnterUpgradeModeEndpoint)


def download_upgrader_on_nodes(instances):
    for node in instances:
        run_upgrade_phase_on_node(node, InstanceControlConsts.PullUpgrade)


def upgrade_nodes(instances):
    for node in instances:
        run_upgrade_phase_on_node(node, InstanceControlConsts.TriggerUpgrade)


def read_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--upgrade_file', '-f', type=str, required=True)

    args = parser.parse_args()
    return args


def upgrader_main():
    args = read_args()
    upgrade_file = Path(args.upgrade_file)

    if NODE_MARKER_PATH.is_file():
        print(f'Please run me on cluster\'s master')
        return

    data = read_cluster_data()
    my_entity = data['my_entity']
    my_node_id = my_entity['node_id']

    instances = data['instances']

    node_instances = [instance for instance in instances if instance['node_id'] != my_node_id]

    print(f'Hello!')
    print(f'You cluster consists of {len(node_instances)} nodes:')
    for node in node_instances:
        print(f'    >>> {node}')

    print(f'Step 1 - shut down adapters on nodes')
    shutdown_adapters(node_instances)

    print(f'Step 2 - Downloading the upgrade on all of the nodes')

    if not upgrade_file.is_file():
        print(f'Upgrade file is missing {upgrade_file}')
        return

    download_upgrader_on_nodes(upgrade_file)

    print(f'UPGRADING MASTER!')
    subprocess.check_call(f'python3 {upgrade_file} --no-research'.split())

    print(f'Step 3 - Trigger the upgrade on the nodes')
    upgrade_nodes(node_instances)


if __name__ == '__main__':
    upgrader_main()
