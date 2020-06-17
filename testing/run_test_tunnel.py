import json
import os
import re
import socket
import sys
import time

import requests

from builds.builds_factory import BuildsInstance
from test_helpers.ci_helper import TeamcityHelper
from testing.test import InstanceManager, execute, ARTIFACTS_DIR_ABSOLUTE, ARTIFACTS_DIR_RELATIVE

DOCKER_INSTALL_COMMANDS = '''
sudo apt update && 
sudo rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock &&
sudo dpkg --configure -a &&
sudo apt -y install apt-transport-https ca-certificates curl software-properties-common && 
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - && 
sudo add-apt-repository 'deb [arch=amd64] https://download.docker.com/linux/ubuntu xenial stable' &&
sudo apt update && 
apt-cache policy docker-ce &&
sudo rm -f /var/lib/dpkg/lock /var/lib/dpkg/lock-frontend &&
sudo dpkg --configure -a && 
sudo apt install -y docker-ce && 
sudo systemctl start docker && 
sudo systemctl enable docker
'''

TUNNEL_INSTALL_CMD = 'curl -b session={session} {url}/api/tunnel/download_agent | sudo /bin/bash'
MAX_503_RETRIES = 40
TC = TeamcityHelper()

API_USER = sys.argv[2]
API_KEY = sys.argv[3]
SAAS_CONTROL_URL = sys.argv[4]
HEADERS = {
    'x-axsaas-apiuser': API_USER,
    'x-axsaas-apikey': API_KEY,
    'CF-Access-Client-Id': sys.argv[5],
    'CF-Access-Client-Secret': sys.argv[6]
}


def delete_stack(stack_id):
    resp = requests.delete(f'{SAAS_CONTROL_URL}/environment_delete/{stack_id}', headers=HEADERS)
    if resp.status_code != 200:
        print(f'Error while deleting the testing stack {resp.content}')
        TC.print(f'Error while deleting the testing stack {resp.content}')
        return
    TC.print(f'Stack {stack_id} deleted successfully')


def main(ami_id=None):
    HEADERS['Content-Type'] = 'application/json'
    with TC.block('Initialize test stack'):
        try:
            resp = requests.post(f'{SAAS_CONTROL_URL}/environment_create', headers=HEADERS,
                                 data=json.dumps({
                                     'company_name': 'ax-saas-test-teamcity',
                                     'customer_email': 'test@axonius.com',
                                     'image_id': ami_id,
                                     'env_type': 'Test'
                                 })
                                 )
            assert resp.status_code == 200
            stack_id = resp.json()['data']['id']
            TC.print(f'Stack ID: {stack_id}')
            print(f'Stack ID: {stack_id}')
            resp.close()
            HEADERS.pop('Content-Type')
        except KeyError:
            print(f'Error in create environment API {resp.content}')
            TC.print(f'Error in create environment API {resp.content}')
            return

        # Takes about 10 minutes to raise the stack machine
        TC.print('Waiting 10 minutes for the stack to initialize')
        time.sleep(600)

    with TC.block('Getting stack information'):
        try:
            resp = requests.get(f'{SAAS_CONTROL_URL}/environment_info/{stack_id}', headers=HEADERS)
            tries = 0
            assert resp.status_code == 200
            while resp.json()['data']['env_status'] != 'READY' and tries < 10:
                resp.close()
                time.sleep(30)
                resp = requests.get(f'{SAAS_CONTROL_URL}/environment_info/{stack_id}', headers=HEADERS)
                tries += 1
                assert resp.status_code == 200

            tunnel_url = resp.json()['data']['env_details']['tunnel_url']
            url = resp.json()['data']['env_details']['machine_url']
            print(f'Tunnel URL: {tunnel_url}')
            print(f'Web URL: {url}')
            TC.print(f'Tunnel URL: {tunnel_url}')
            TC.print(f'Web URL: {url}')
        except KeyError:
            print(f'Error in getting stack info {resp.content}')
            TC.print(f'Error in getting stack info {resp.content}')
            delete_stack(stack_id)
        except AssertionError:
            print(f'Error in response from SaaS Control API - Status Code: {resp.status_code}, Error: {resp.content}')
            TC.print(
                f'Error in response from SaaS Control API - Status Code: {resp.status_code}, Error: {resp.content}')
            delete_stack(stack_id)

    try:
        with TC.block('Raising GCP tunnel machine'):
            instance_manager = InstanceManager('gcp', 'n1-standard-8', 1)

            instance_manager._InstanceManager__instances, group_name = \
                instance_manager._InstanceManager__builds.create_instances(
                    'Sagi-Tunnel-tests',
                    instance_manager.instance_type,
                    instance_manager.number_of_instances,
                    instance_cloud=instance_manager._InstanceManager__builds.CloudType.GCP,
                    instance_image='ubuntu-test-machine-2',
                    force_password_change=True
                )
            instance = instance_manager._InstanceManager__instances[0]
            instance.wait_for_ssh()
            TC.print(f'GCP Tunnel machine raised: {instance.ip}, Credentials: ubuntu:{instance.ssh_pass}')

            # Install docker
            try:
                TC.print('Installing docker-ce on tunnel machine')
                instance_manager._InstanceManager__ssh_execute(instance, 'Install docker daemon on server',
                                                               DOCKER_INSTALL_COMMANDS,
                                                               append_ts=False)
            except Exception:
                # Sometimes it has apt lock problems and stuff, give it another try in a minute
                time.sleep(60)
                instance_manager._InstanceManager__ssh_execute(instance, 'Install docker daemon on server',
                                                               DOCKER_INSTALL_COMMANDS,
                                                               append_ts=False)
            instance.wait_for_ssh()

            # Check docker installed successfully
            assert 'permission denied' not in \
                   instance_manager._InstanceManager__ssh_execute(instance,
                                                                  'Check docker installation',
                                                                  'sudo docker ps',
                                                                  append_ts=False)
            TC.print('docker-ce installed successfully')

        def _wait_for_hostname_to_resolv():
            try:
                socket.gethostbyname(tunnel_url)
            except OSError:
                time.sleep(20)
                _wait_for_hostname_to_resolv()

        _wait_for_hostname_to_resolv()

        axonius_instance = BuildsInstance(
            cloud=instance_manager._InstanceManager__builds.CloudType.AWS,
            instance_id=stack_id,
            ip=tunnel_url,
            ssh_user='ubuntu',
            ssh_pass='bringorder'
        )
        axonius_instance.wait_for_ssh()
        TC.print('Connected to stack machine using ssh')

        client_rb_file = instance_manager._InstanceManager__ssh_execute(axonius_instance,
                                                                        'Get Node id',
                                                                        'sudo cat /etc/chef/client.rb',
                                                                        append_ts=False)
        TC.print(f'client.rb file content: {client_rb_file}')

        # Create a copy of the testing folder and copy it to there.
        print(f'Creating source code tar and copying it..')
        execute('rm -rf testing.tar.gz')
        execute('tar czf testing.tar.gz testing/*')
        print(f'Transferring testing.tar.gz to stack..')
        with open('testing.tar.gz', 'rb') as fh:
            axonius_instance.put_file(fh, '/home/ubuntu/cortex/testing.tar.gz')
        instance_manager._InstanceManager__ssh_execute(axonius_instance,
                                                       'Unpack testing folder',
                                                       'cd /home/ubuntu/cortex; sudo rm -rf testing; sudo tar xzf testing.tar.gz; sudo chown -R ubuntu:ubuntu testing/',
                                                       append_ts=False)
        TC.print('Uploaded and extracted testing folder')

        tries_counter = 0
        while requests.get(url).status_code == 503 or tries_counter > MAX_503_RETRIES:
            # AWS Health checker yet to recognize server has finished initializing
            print(f'Iteration {tries_counter+1} of 503s')
            time.sleep(20)
            tries_counter += 1

        if tries_counter > MAX_503_RETRIES:
            raise Exception('Server keeps returning 503')

        # Get session id
        TC.print('Getting session id from stack machine')
        resp = requests.post(f'{url}/api/login',
                             data='{"user_name":"admin2","password":"kjhsjdhbfnlkih43598sdfnsdfjkh","remember_me":false}')
        session = re.findall('session=(.*?);', resp.headers['Set-Cookie'])[0]
        resp.close()

        # Connection will probably disconnect till it gets here
        instance.wait_for_ssh()

        TC.print(f'Got session id: {session}')

        # Download and install tunnel container
        instance_manager._InstanceManager__ssh_execute(instance, 'Download and install tunnel container',
                                                       TUNNEL_INSTALL_CMD.format(session=session, url=url),
                                                       append_ts=False)
        TC.print('Downloaded and installed tunnel container successfully on GCP machine')

        # Connection will probably disconnect till it gets here
        axonius_instance.wait_for_ssh()

        # Start Selenium container
        instance_manager._InstanceManager__ssh_execute(axonius_instance,
                                                       'Start Selenium container',
                                                       'cd /home/ubuntu/cortex; . ./prepare_python_env.sh; sh ./testing/test_credentials/docker_login.sh; python -c \'from services.standalone_services.selenium_service import SeleniumService; a = SeleniumService(); a.build(); a.take_process_ownership(); a.start()\'',
                                                       append_ts=False)
        TC.print('Started selenium container on stack machine')

        # Change permissions
        instance_manager._InstanceManager__ssh_execute(axonius_instance, 'Change axonius_settings folder permissions',
                                                       'sudo chown -R ubuntu:ubuntu /home/ubuntu/cortex/.axonius_settings',
                                                       append_ts=False,
                                                       timeout=600)

        # Start Tunnel tests
        TC.print('Starting tunnel pytest')
        instance_manager._InstanceManager__ssh_execute(axonius_instance, 'Start tunnel tests',
                                                       'cd /home/ubuntu/cortex; . ./prepare_python_env.sh; mkdir logs/TC_logs; cd ./testing/ui_tests; python3 -m pytest -v --junit-xml=/home/cortex/logs/TC_logs/ tests/test_tunnel.py',
                                                       append_ts=False,
                                                       timeout=600)

        TC.print('Creating tarball from artifacts')
        instance_manager._InstanceManager__ssh_execute(axonius_instance, 'Creating tar for artifacts',
                                                       'cd /home/ubuntu/cortex/logs; tar czf /home/ubuntu/cortex/TC_logs.tar.gz TC_logs/*',
                                                       append_ts=False)
        TC.print('Getting tarball from server')
        with open(os.path.join(ARTIFACTS_DIR_ABSOLUTE, 'TC_logs.tar.gz'), 'wb') as fh:
            fh.write(axonius_instance.get_file('/home/ubuntu/cortex/TC_logs.tar.gz'))

        TC.print('Publishing artifacts')
        execute(f'cd {ARTIFACTS_DIR_ABSOLUTE}; tar xvzf TC_logs.tar.gz')
        TC.publishArtifacts(ARTIFACTS_DIR_RELATIVE)
        #TC.importData('junit', os.path.join(ARTIFACTS_DIR_RELATIVE, job_name, 'xml'))

    except Exception as e:
        print(f'Exception happened while trying to test tunnel {str(e)}')
    finally:
        # Terminate instance machine (Stack machine will get terminated in the sh script)
        instance_manager._InstanceManager__builds.terminate_all()
        delete_stack(stack_id)
        print('Terminated regular tunnel machine')
        TC.print('Terminated regular tunnel machine')


if __name__ == '__main__':
    main(ami_id=sys.argv[1])
