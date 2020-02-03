#!/usr/bin/env python3

import json
import subprocess
import shlex
import argparse
from pathlib import Path
import shutil

from axonius.consts.instance_control_consts import InstanceControlConsts
from axonius.consts.system_consts import NODE_MARKER_PATH
from scripts.maintenance_tools.cluster_reader import read_cluster_data


def curl_in_docker_network(docker_dns, endpoint):
    env = {'DOCKER_HOST': 'unix:///var/run/weave/weave.sock'}
    output = subprocess.check_output(
        shlex.split(f'docker run --rm appropriate/curl -kfsSL https://{docker_dns}.axonius.local:443/api/{endpoint}'),
        env=env, timeout=60 * 2)
    output = output.decode().strip()
    print(output)


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

    data = json.loads(read_cluster_data())
    my_entity = data['my_entity']
    my_node_id = my_entity['node_id']

    instances = data['instances']

    node_instances = [instance for instance in instances if instance['node_id'] != my_node_id]

    print(f'Hello!')
    print(f'You cluster consists of {len(node_instances)} nodes:')
    for node in node_instances:
        print(f'    >>> {node}')

    print(f'Step 1 - shut down adapters on nodes')
    for node in node_instances:
        node_id = node['node_id']
        instance_control_name = node['plugin_unique_name']
        print(f'Shutting down adapters on node {node_id} ({instance_control_name})')
        curl_in_docker_network(instance_control_name, InstanceControlConsts.EnterUpgradeModeEndpoint)

    print(f'Step 2 - Downloading the upgrade on all of the nodes')

    if not upgrade_file.is_file():
        print(f'Upgrade file is missing {upgrade_file}')
        return

    shutil.copy(upgrade_file, '/home/ubuntu/cortex/testing/services/plugins/httpd_service/httpd/upgrade.py')

    for node in node_instances:
        node_id = node['node_id']
        instance_control_name = node['plugin_unique_name']
        print(f'Pulling upgrade {node_id} ({instance_control_name})')
        curl_in_docker_network(instance_control_name, InstanceControlConsts.PullUpgrade)

    print(f'UPGRADING MASTER!')
    subprocess.check_call(f'python3 {upgrade_file} --no-research'.split())

    print(f'Step 3 - Trigger the upgrade on the nodes')
    for node in node_instances:
        node_id = node['node_id']
        instance_control_name = node['plugin_unique_name']
        print(f'trigger the upgrade {node_id} {instance_control_name}')
        curl_in_docker_network(instance_control_name, InstanceControlConsts.TriggerUpgrade)


if __name__ == '__main__':
    upgrader_main()
