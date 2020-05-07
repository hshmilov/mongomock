import json
import subprocess

from axonius.utils.network.docker_network import run_cmd_in_container
from axonius.consts.instance_control_consts import InstanceControlConsts
from scripts.instances.instances_consts import MASTER_ADDR_HOST_PATH
from services.weave_service import is_using_weave


def read_cluster_data():
    cluster = run_cmd_in_container('instance-control',
                                   f'curl -kfsSL https://localhost/api/{InstanceControlConsts.DescribeClusterEndpoint}')
    cluster = json.loads(cluster)
    if MASTER_ADDR_HOST_PATH.is_file():
        cluster['instance_type'] = 'node'
        cluster['master_ip'] = MASTER_ADDR_HOST_PATH.read_text()
    else:
        cluster['instance_type'] = 'master'
    if is_using_weave():
        cluster['network'] = subprocess.check_output('weave status connections'.split(), timeout=60).decode()
    return json.dumps(cluster)


if __name__ == '__main__':
    print(read_cluster_data())
