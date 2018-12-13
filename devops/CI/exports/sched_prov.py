#!/usr/bin/env python3
import os
import random
import shlex
import subprocess
import sys
import shutil
from pathlib import Path

from urllib3 import ProxyManager

if os.geteuid() != 0:
    print('This script should run as root')
    sys.exit(-1)

PIDFILE = Path('/tmp/sched_prov.pid')
PROVISION_MARKER = Path('/home/ubuntu/CHEF_PROVISION.marker')

if PIDFILE.is_file():
    print(f'{PIDFILE} already exists')
    sys.exit(-1)

if not PROVISION_MARKER.is_file():
    print(f'{PROVISION_MARKER} does not exist, already provisioned')
    sys.exit(-1)


def chech_command_status(cmd, **kwargs):
    return run_command(cmd, **kwargs).returncode


def run_command(cmd, **kwargs):
    return subprocess.run(shlex.split(cmd), **kwargs)


def read_proxy_data():
    try:
        proxy_line = run_command('docker exec core cat /tmp/proxy_data.txt', stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).stdout.decode().strip()
        print(f'Got proxy line={proxy_line}')
        # invoking this one only to validate that the proxy string format is a valid proxy string
        ProxyManager(f'http://{proxy_line}')
        return proxy_line
    except Exception as e:
        print(f'Failed to process proxy line {e}')
        return None


def provision():
    if chech_command_status('pgrep -x chef-client') == 0:
        print('chef client already running')
    else:
        print('starting provision sequence')
    node_name = 'node-' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))

    shutil.rmtree('/etc/chef')
    Path('/etc/chef').mkdir(mode=0o750)

    client_rb_template = f'chef_server_url  "https://diag-c.axonius.com/organizations/axonius"\n' + \
                         f'node_name  "{node_name}"\n' + \
                         f'validation_key "/home/ubuntu/axonius-validator.pem"\n' + \
                         f'validation_client_name "axonius-validator"\n'

    proxy_line = read_proxy_data()
    if proxy_line:
        http_proxy = f'http://{proxy_line}'
        https_proxy = f'https://{proxy_line}'
        client_rb_template += f'http_proxy "{http_proxy}"\n' + \
                              f'https_proxy "{https_proxy}"\n'

    Path('/etc/chef/client.rb').write_text(client_rb_template)

    first_boot = '''
    {
         "chef_environment": "prod",
         "run_list" :[
         "role[provision]",
         "role[after_provision]"
         ]
    }
    '''
    Path('/etc/chef/first-boot.json').write_text(first_boot)

    run_command('/usr/bin/chef-client -j /etc/chef/first-boot.json')
    run_command('/usr/sbin/service chef-client restart')


try:
    PIDFILE.touch()
    provision()
finally:
    PIDFILE.unlink()
