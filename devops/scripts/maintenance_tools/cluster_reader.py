import json
import subprocess

from axonius.utils.network.docker_network import run_cmd_in_container
from axonius.consts.instance_control_consts import InstanceControlConsts
from scripts.instances.instances_consts import MASTER_ADDR_HOST_PATH
from services.weave_service import is_using_weave, is_weave_up


def read_cluster_data():
    try:
        cluster = run_cmd_in_container('instance-control',
                                       f'curl -kfsSL https://127.0.0.1/api/{InstanceControlConsts.DescribeClusterEndpoint}')
        cluster = json.loads(cluster)
        if MASTER_ADDR_HOST_PATH.is_file():
            cluster['instance_type'] = 'node'
            cluster['master_ip'] = MASTER_ADDR_HOST_PATH.read_text()
        else:
            cluster['instance_type'] = 'master'
        if is_using_weave() and is_weave_up():
            cluster['network'] = subprocess.check_output('weave status connections'.split(), timeout=60).decode()
        return cluster
    except Exception:
        print(f'Failed reading cluster data. returning None')
        return None


if __name__ == '__main__':
    print(json.dumps(read_cluster_data()))
