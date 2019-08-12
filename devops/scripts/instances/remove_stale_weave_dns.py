"""
Sometimes, weave dns does not clean leftovers of dead containers. This leads to the situation where a specific host
can be assigned the same ip. More information can be viewed here:
https://github.com/weaveworks/weave/issues/3432
ahttps://axonius.atlassian.net/browse/AX-4731

This script examines each dns entry, sees if its valid or not and if not removes it and then
restarts the relevant container.

Warning - this does not work on multi-node !
"""
import sys
import subprocess
from collections import defaultdict

import requests
import docker

WEAVE_API = 'http://127.0.0.1:6784'
CORTEX_CWD = '/home/ubuntu/cortex'


def request_weave(method, endpoint: str):
    dns_results = requests.request(method, f'{WEAVE_API}/{endpoint}')
    dns_results.raise_for_status()
    return dns_results.text


def dprint(format_string):
    print(f'[REMOVE_DEAD_WEAVE_IPS]: {format_string}')


def main():
    try:
        _, action = sys.argv    # pylint: disable=unbalanced-tuple-unpacking
        assert action in ['dry', 'wet']
    except Exception:
        dprint(f'Usage: wet/dry')
        return -1

    client = docker.from_env(environment={'DOCKER_HOST': 'unix:///var/run/weave/weave.sock'})
    container_ids = []
    for container in client.containers.list():
        container_ids.append(container.id)

    dns_results = request_weave('GET', 'status/dns').strip()
    weave_hostname_to_cid = defaultdict(list)
    for line in dns_results.splitlines():
        dns_hostname, ip, container_short_id, mac = line.split()
        weave_hostname_to_cid[dns_hostname.strip()].append(container_short_id.strip())
        if not any(cid.startswith(container_short_id) for cid in container_ids):
            dprint(f'Found stale! {dns_hostname} / {ip} / {container_short_id}')
            if action == 'wet':
                request_weave('DELETE', f'name/*/{ip.strip()}?fqdn={dns_hostname.strip()}.axonius.local')
                dprint(f'deleted {dns_hostname} / {ip} / {container_short_id}')

    for hostname, container_ids in weave_hostname_to_cid.items():
        if len(container_ids) > 1:
            if '_adapter' in hostname:
                adapter_name = hostname.split('_adapter')[0]
                dprint(f'adapter {adapter_name} needs to be restarted.')
            else:
                adapter_name = None
                dprint(f'Can not get adapter name! Container {hostname} needs to be restarted.')
            if action == 'wet' and adapter_name:
                try:
                    subprocess.check_call(
                        f'./axonius.sh adapter {adapter_name} up --restart --prod', shell=True, cwd=CORTEX_CWD
                    )
                except Exception:
                    dprint(f'Warning! could not restart adapter {adapter_name}! continuing')

    dprint('done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
