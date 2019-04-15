"""
Does everything.
"""
import os
import random
import socket
import string
import sys
import time

from enum import Enum
from typing import List

import paramiko
import requests
import urllib3

# surpress warning messages about vaildation error
from retrying import retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# its debug by default
IS_DEBUG = True
BUILDS_AUTH_TOKEN = 'c9129428-1973-45e2-94e2-8cca92a31350'
BUILDS_URL = 'builds-local.axonius.lan' if 'BUILDS_HOST' not in os.environ else os.environ['BUILDS_HOST']
DAILY_EXPORT_SUFFIX = '_daily_export'

SSH_NETWORK_TIMEOUT = 60 * 90  # some commands are really long...
TIME_TO_WAIT_BETWEEN_SSH_CONNECT_TRIES = 5
MAX_SSH_TRIES = 60
MAX_TIMEOUT_FOR_TRANSFERS = 60 * 10
SSH_BUFFER_SIZE = 100   # We read in these chunks. In case of a timeout, we lose the last chunk.


def debug_print(print_str):
    if IS_DEBUG is True:
        print('[+] {0}'.format(print_str))


class BuildsAPI:
    def __init__(self):
        pass

    @staticmethod
    def request(method, endpoint, data=None, json_data=None, params=None):
        headers = {'x-auth-token': BUILDS_AUTH_TOKEN}

        debug_print(f'Sending request to {endpoint} with {data}, {json_data}, {params}')
        response = requests.request(
            method, f'https://{BUILDS_URL}/api/{endpoint}',
            data=data, json=json_data, params=params, verify=False, headers=headers
        )
        try:
            response.raise_for_status()
            return response.json()
        except Exception:
            debug_print(f'Got errornous response {response.content.decode("utf-8")}')
            raise

    def get(self, *args, **kwargs):
        return self.request('GET', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request('POST', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.request('DELETE', *args, **kwargs)


class BuildsInstance(BuildsAPI):
    def __init__(self, cloud, instance_id, ip, ssh_user, ssh_pass):
        super().__init__()
        self.cloud = cloud
        self.id = instance_id
        self.ip = ip
        self.ssh_user = ssh_user
        self.ssh_pass = ssh_pass
        self.initialized = False

        self.sshc = paramiko.SSHClient()
        self.sshc.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.sftp = None

    def __str__(self):
        return f'{self.cloud}-{self.id}-{self.ip}'

    def debug_print(self, print_string):
        debug_print(f'{self}:\t{print_string}')

    def wait_for_ssh(self):
        num_tries = 0
        connected = False

        # We try to connect numerous of times, because it takes time until a new instance is ready.
        while connected is False:
            try:
                self.debug_print('Trying to ssh.. (attempt {0})'.format(num_tries))
                self.sshc.connect(self.ip, username=self.ssh_user, password=self.ssh_pass, timeout=60, auth_timeout=60)
                self.sftp = self.sshc.open_sftp()
                connected = True
            except (TimeoutError, paramiko.SSHException, paramiko.ssh_exception.NoValidConnectionsError):
                num_tries += 1
                if num_tries == MAX_SSH_TRIES:
                    raise
            except Exception as exc:
                if exc.args[0] == 'timed out':
                    num_tries += 1
                    if num_tries == MAX_SSH_TRIES:
                        raise
                else:
                    raise

            time.sleep(TIME_TO_WAIT_BETWEEN_SSH_CONNECT_TRIES)

        self.debug_print('Connected via SSH.')
        self.initialized = True

    def ssh(self, command, quiet=True, timeout=None):
        """
        Runs a command and returns its output. not interactive.
        :param quiet: Should not write debug print.
        :param command: the command.
        :param timeout: optional timeout for command
        :return: (stdout, stderr).
        """
        assert self.initialized, 'Instance is not initialized, please use wait_for_ssh'

        if not quiet:
            self.debug_print('Running ssh: {0}'.format(command))

        chan = self.sshc.get_transport().open_session(timeout=timeout or SSH_NETWORK_TIMEOUT)
        chan.set_combine_stderr(True)
        chan.settimeout(timeout or SSH_NETWORK_TIMEOUT)
        stdout = chan.makefile()
        chan.exec_command(command)

        output = b''
        try:
            while True:
                current = stdout.read(SSH_BUFFER_SIZE)
                if not current:
                    break
                output += current
            rc = chan.recv_exit_status()
        except socket.timeout:
            # Timeout
            rc = -1

        output = output.strip().decode('utf-8')
        return rc, output

    def get_file(self, file_path):
        assert self.initialized, 'Instance is not initialized, please use wait_for_ssh'
        with self.sftp.open(file_path, 'r') as remote_file:
            return remote_file.read()

    def put_file(self, file_object, remote_file_path):
        self.sftp.putfo(file_object, remote_file_path)

    def get_folder_as_tar(self, remote_file_path):
        assert self.initialized, 'Instance is not initialized, please use wait_for_ssh'
        rc, output = self.ssh(f'tar -czf /tmp/tmp.tar {remote_file_path}')
        assert rc == 0, f'Error in compressing remote folder: {output}'
        return self.get_file('/tmp/tmp.tar')

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def terminate(self):
        self.post(f'instances/{self.cloud}/{self.id}/delete')


class Builds(BuildsAPI):
    class VmTypeEnum(Enum):
        Instance = 'Builds-VM'
        Demo = 'Demo-VM'
        AutoTest = 'Auto-Test-VM'

    class CloudType(Enum):
        AWS = 'aws'
        GCP = 'gcp'

    def __init__(self):
        super().__init__()
        self.instances: List[BuildsInstance] = []
        self.groups: List[str] = []

    def get_latest_daily_export(self):
        response = self.get('exports', params={'limit': 10})
        daily_exports = [export for export in response['result'] if DAILY_EXPORT_SUFFIX in export['version']]
        return daily_exports[0]

    def get_last_exports(self, limit=10):
        response = self.get('exports', params={'limit': limit})
        return response

    def create_instances(
            self,
            group_name: str,
            instance_type: str,
            num: int,
            vm_type: VmTypeEnum = VmTypeEnum.AutoTest,
            instance_cloud: CloudType = CloudType.GCP,
            key_name: str = None,
            instance_image: str = None,
            predefined_ssh_username: str = None,
            predefined_ssh_password: str = None

    ) -> (List[BuildsInstance], str):
        request_obj = {
            'name': group_name,
            'type': instance_type,
            'cloud': instance_cloud.value,
            'vm_type': vm_type.value,
            'num': num,
        }

        if key_name:
            request_obj['key_name'] = key_name

        if instance_image:
            request_obj['image'] = instance_image

        custom_code = ''
        if predefined_ssh_username and predefined_ssh_password:
            username = predefined_ssh_username
            password = predefined_ssh_password
        else:
            username = 'ubuntu'
            password = ''.join(random.SystemRandom().choices(
                string.ascii_uppercase + string.ascii_lowercase + string.digits, k=32)
            )
            custom_code = f"""
            #!/bin/bash
            echo ubuntu:{password}| chpasswd
            sed -i.bak 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
            sed -i.bak 's/127\.0\.1\.1.*/127.0.1.1\t'`hostname`'/' /etc/hosts\n
            service ssh restart"""

        request_obj['config'] = {
            'custom_code': custom_code
        }

        result = self.post('instances', json_data=request_obj)
        result_instances = result['instances']
        result_group_name = result['group_name']
        instances = []

        for instance_data in result_instances:
            instances.append(
                BuildsInstance(
                    instance_cloud.value,
                    instance_data['id'],
                    instance_data['private_ip'],
                    username,
                    password
                )
            )

        self.instances.extend(instances)
        self.groups.append(result_group_name)

        return instances, result_group_name

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def terminate_group(self, group_name):
        self.post(f'groups/delete?async=true', json_data={'group_name': group_name})

    def terminate_all(self):
        for group in self.groups:
            try:
                print(f'Terminating group {group}...')
                self.terminate_group(group)
            except Exception as e:
                print(f'Could not terminate {group}, bypassing: {e}', file=sys.stderr, flush=True)
