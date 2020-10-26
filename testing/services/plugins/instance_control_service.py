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
        self.rsa_keys = f'{self.service_dir}/rsa_keys'
        self.ssh_key_filename = os.path.join(self.rsa_keys, 'id_rsa')

    def __create_rsa_keys(self):
        '''
        Creates rsa_keys and rsa_keys.pub for ssh
        :return:
        '''

        if os.path.exists(self.ssh_key_filename):
            print('ssh key already exists')
            return
        if os.path.exists(self.rsa_keys) and os.path.isfile(self.rsa_keys):
            # Remains from old version before container host
            os.remove(self.rsa_keys)
        if not os.path.exists(self.rsa_keys):
            os.mkdir(self.rsa_keys)

        # ssh-keygen -b 2048 -t rsa -f rsa_keys -q -N ""
        print(f'making ssh key with uid {os.getuid()}')
        assert subprocess.check_call(['ssh-keygen', '-b', '2048', '-m', 'PEM', '-t', 'rsa', '-f', self.ssh_key_filename,
                                      '-q', '-N', '']) == 0
        print('made ssh key!')

        with open(os.path.join(self.rsa_keys, 'authorized_keys'), 'a') as ssh_file:
            with open(f'{self.ssh_key_filename}.pub') as rsa_pkey:
                ssh_file.write('# Instance key\n')
                ssh_file.write(rsa_pkey.read())

        print(f'Added authorized_keys at: {os.path.join(self.rsa_keys, "authorized_keys")}')

    # pylint: disable=W0221
    def start(self, *args, **kwargs):
        self.__create_rsa_keys()
        try:
            subprocess.check_call(f'chown -R root:root {self.rsa_keys}'.split(' '))
        except Exception:
            pass
        return super().start(*args, **kwargs)

    @property
    def volumes_override(self):
        volumes = [f'{self.rsa_keys}:/home/axonius/app/rsa_keys',
                   f'/etc/hostname:{HOSTNAME_FILE_PATH}', f'{self.service_dir}/metrics:/home/axonius/app/metrics']
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
