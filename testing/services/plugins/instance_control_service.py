import os
import subprocess

import pytest
from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture
from axonius.consts.system_consts import CORTEX_PATH
from axonius.consts.instance_control_consts import HOSTNAME_FILE_PATH


class InstanceControlService(PluginService):
    def __init__(self):
        super().__init__('instance-control')

    def __create_rsa_keys(self):
        """
        Creates rsa_keys and rsa_keys.pub for ssh
        :return:
        """
        rsa_keys = f'{self.service_dir}/rsa_keys'
        if os.path.exists(rsa_keys):
            print('ssh key already exists')
            return

        # ssh-keygen -b 2048 -t rsa -f rsa_keys -q -N ""
        print(f'making ssh key with uid {os.getuid()}')
        assert subprocess.check_call(['ssh-keygen', '-b', '2048', '-t', 'rsa', '-f', rsa_keys,
                                      '-q', '-N', '']) == 0
        print('made ssh key!')

        ssh_dir = '/home/ubuntu/.ssh'
        if not os.path.exists(ssh_dir):
            print(f'mkdir {ssh_dir}')
            os.mkdir(ssh_dir)

        with open(os.path.join(ssh_dir, 'authorized_keys'), 'a') as ssh_file:
            with open(f'{rsa_keys}.pub') as rsa_pkey:
                ssh_file.write('# Instance key\n')
                ssh_file.write(rsa_pkey.read())

    # pylint: disable=W0221
    def start(self, *args, **kwargs):
        self.__create_rsa_keys()
        return super().start(*args, **kwargs)

    @property
    def volumes_override(self):
        volumes = [f'{self.service_dir}/rsa_keys:/home/axonius/app/rsa_keys',
                   f'/etc/hostname:{HOSTNAME_FILE_PATH}:ro']
        volumes.extend(super().volumes_override)
        return volumes

    @property
    def environment(self):
        env = super().environment
        env.append(f'CORTEX_PATH={CORTEX_PATH}')
        return env


@pytest.fixture(scope='module')
def image_control_fixture(request):
    service = InstanceControlService()
    initialize_fixture(request, service)
    return service
