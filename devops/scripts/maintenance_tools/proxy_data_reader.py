import json

from axonius.utils.network.docker_network import run_cmd_in_container
from axonius.consts.instance_control_consts import InstanceControlConsts


def read_proxy_data():
    try:
        output = run_cmd_in_container('instance-control',
                                      f'curl -kfsSL https://localhost/api/{InstanceControlConsts.ReadProxySettings}')
        output = json.loads(output)
        return output
    except Exception as e:
        print(f'Failed reading cluster data. returning None {e}')
        return None


if __name__ == '__main__':
    print(json.dumps(read_proxy_data()))
