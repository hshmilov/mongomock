#!/usr/bin/env python3

import json
import subprocess
import shlex
import argparse
from pathlib import Path
import shutil

import requests

from axonius.consts.instance_control_consts import InstanceControlConsts
from axonius.consts.system_consts import NODE_MARKER_PATH, DOCKERHUB_URL
from scripts.instances.network_utils import weave_dns_lookup
from scripts.maintenance_tools.cluster_reader import read_cluster_data

REQUEST_TIMEOUT = 60 * 30


def request_instance_control(plugin_unique_name, endpoint):
    plugin_unique_name_ip = weave_dns_lookup(plugin_unique_name)
    res = requests.get(f'https://{plugin_unique_name_ip}:443/api/{endpoint}', verify=False,
                       timeout=REQUEST_TIMEOUT)
    print(res.text.strip())


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
