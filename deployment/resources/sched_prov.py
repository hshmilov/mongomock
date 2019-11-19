#!/usr/bin/env python3
import json
import os
import random
import shlex
import subprocess
import sys
import shutil
import urllib.request
from pathlib import Path

from urllib3 import ProxyManager

PIDFILE = Path('/tmp/sched_prov.pid')
PROVISION_MARKER = Path('/home/ubuntu/CHEF_PROVISION.marker')
NODE_MARKER_PATH_HOST = '/home/ubuntu/cortex/.axonius_settings/connected_to_master.marker'
CREDS = 'creds'
VERIFY = 'verify'

SCALYR_TEMPLATE = '''
// Configuration for the Scalyr Agent. For help:
//
// https://www.scalyr.com/help/scalyr-agent-2

{{
  api_key: "{API_KEY}",

  {PROXY_SECTION}

  server_attributes: {{
     // Fill in this field if you'd like to override the server's hostname.
     serverHost: "{NODE_NAME}",

     // You can add whatever additional fields you'd like.
     tier: "{TIER}"
  }},

  // Log files to upload to Scalyr. You can use '*' wildcards here.
  logs: [
     {{
        path: "/var/log/syslog",
        attributes: {{parser: "rawlog"}}
     }},
     {{
        path:"/home/ubuntu/helper.log",
        attributes: {{parser: "rawlog"}}
     }},
     {{
        path: "/home/ubuntu/.bash_history",
        attributes: {{parser: "rawlog"}}
     }},
     {{
        path: "/var/log/auth.log",
        attributes: {{parser: "rawlog"}}
     }},
     {{
        path: "/var/log/chef_scheduled_provision.log",
        attributes: {{parser: "rawlog"}}
     }},
     {{
       path: "/var/log/machine_boot.log",
       attributes: {{parser: "rawlog"}}
     }}
  ]
}}
'''

PROXY_TEMPLATE = '''
   "use_requests_lib": true,
   "https_proxy": "{PROXY_STRING}",
 '''


def chech_command_status(cmd, **kwargs):
    return run_command(cmd, **kwargs).returncode


def run_command(cmd, **kwargs):
    return subprocess.run(shlex.split(cmd), **kwargs)


def is_this_node_host():
    return Path(NODE_MARKER_PATH_HOST).is_file()


def read_proxy_data():
    try:

        if is_this_node_host():
            print('running on node')
            return {CREDS: 'localhost:8888', VERIFY: False}

        # harcoded path since this script doesn't has the venv
        new_proxy_data_file = Path('/home/ubuntu/cortex/.axonius_settings/proxy_data.json')
        if new_proxy_data_file.is_file():
            proxy_data = new_proxy_data_file.read_text()
        else:  # backward compatibility
            proxy_data = run_command('docker exec core cat /tmp/proxy_data.txt', stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE).stdout.decode()

        proxy_data = proxy_data.strip()
        try:
            as_dict = json.loads(proxy_data)
            proxy_creds = as_dict[CREDS]
        except Exception as e:
            # backward compatibility, when the file was a single proxy_line
            proxy_creds = proxy_data
            as_dict = {CREDS: proxy_data, VERIFY: True}

        print(f'Got proxy line={proxy_creds}')
        # invoking this one only to validate that the proxy string format is a valid proxy string
        ProxyManager(f'http://{proxy_creds}')
        return as_dict
    except Exception as e:
        print(f'Failed to process proxy line {e}')
        return None


def is_local_node():
    try:
        # no-venv, can not import request and the url
        # our dns is not good enough: 10.0.2.110 is services.axonius.lan
        return json.loads(urllib.request.urlopen('http://10.0.2.110:8080/axonius-local.json').read()
                          .decode())['local'] is True
    except Exception:
        return False


def configure_scalyr_for_pre_provision(proxy_line, node_name, api_key, tier):
    proxy_section = ''
    if proxy_line:
        proxy_section = PROXY_TEMPLATE.format(PROXY_STRING=f'https://{proxy_line}')
    template = SCALYR_TEMPLATE.format(API_KEY=api_key,
                                      PROXY_SECTION=proxy_section,
                                      NODE_NAME=node_name,
                                      TIER=tier)

    Path('/etc/scalyr-agent-2/agent.json').write_text(template)
    run_command('/usr/sbin/service scalyr-agent-2 restart')


def provision():
    node_name_file = Path('/tmp/chef_node_name')
    if chech_command_status('pgrep -x chef-client') == 0:
        print('chef client already running')
    else:
        print('starting provision sequence')

    is_node_local = is_local_node()

    if not node_name_file.exists():
        random_part = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        if is_node_local:
            node_name = 'node-ax-' + random_part
        else:
            node_name = 'node-' + random_part
        node_name_file.write_text(node_name)

        shutil.rmtree('/etc/chef')
        Path('/etc/chef').mkdir(mode=0o750)
    else:
        node_name = node_name_file.read_text()

    client_rb = Path('/etc/chef/client.rb')

    client_rb_template = [f'chef_server_url  "https://manage.chef.io/organizations/axonius"',
                          f'node_name  "{node_name}"',
                          f'validation_key "/home/ubuntu/axonius-validator-2.pem"',
                          f'validation_client_name "axonius-validator-2"']

    client_rb_template.append(
        'automatic_attribute_blacklist [["filesystem","by_mountpoint"], ["filesystem","by_pair"], '
        '["network", "interfaces"], ["counters", "network"], ["dmi"], ["packages"]]')

    proxy_data = read_proxy_data()
    proxy_line = proxy_data[CREDS]
    if proxy_line:
        http_proxy = f'http://{proxy_line}'
        https_proxy = f'https://{proxy_line}'
        client_rb_template.append(f'http_proxy "{http_proxy}"')
        client_rb_template.append(f'https_proxy "{https_proxy}"')

        if proxy_data[VERIFY] is False:
            client_rb_template.append(f'ssl_verify_mode :verify_none')

    client_rb.write_text('\n'.join(client_rb_template))

    first_boot = '''
    {
         "chef_environment": "prod",
         "run_list" :[
         "role[provision]",
         "role[after_provision]"
         ]
    }
    '''

    try:
        tier = 'pre_prov_test' if is_node_local else 'pre_prov'
        configure_scalyr_for_pre_provision(proxy_line=proxy_line,
                                           node_name=node_name,
                                           api_key=Path('/home/ubuntu/pre-prov-scalyr.key').read_text().strip(),
                                           tier=tier)
    except Exception as e:
        print(f'Failed to pre-configure scalyr {e}')

    Path('/etc/chef/first-boot.json').write_text(first_boot)

    with open('/home/ubuntu/helper.log', 'wb') as helper:
        run_command('/sbin/ifconfig', stdout=helper, stderr=helper)
        run_command('cat /etc/resolv.conf', stdout=helper, stderr=helper)
        run_command('/usr/bin/chef-client -j /etc/chef/first-boot.json -l debug', stdout=helper, stderr=helper)
        run_command('/usr/sbin/service chef-client restart', stdout=helper, stderr=helper)


def main():
    if os.geteuid() != 0:
        print('This script should run as root')
        sys.exit(-1)

    if PIDFILE.is_file():
        print(f'{PIDFILE} already exists')
        sys.exit(-1)

    if not PROVISION_MARKER.is_file():
        print(f'{PROVISION_MARKER} does not exist, already provisioned')
        sys.exit(-1)

    try:
        PIDFILE.touch()
        provision()
    finally:
        PIDFILE.unlink()


if __name__ == '__main__':
    main()
