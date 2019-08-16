import os
import subprocess
from pathlib import Path

import pytest

from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture


class InstanceControlService(PluginService):
    def __init__(self):
        super().__init__('instance-control')

    def __create_rsa_keys(self):
        """
        Creates rsa_keys and rsa_keys.pub for ssh
        :return:
        """
        rsa_keys = f'{self.service_dir}/rsa_keys'
        if not os.path.exists(rsa_keys):
            # ssh-keygen -b 2048 -t rsa -f rsa_keys -q -N ""
            print(f'making ssh key with uid {os.getuid()}')
            assert subprocess.check_call(['ssh-keygen', '-m', 'PEM', '-b', '2048', '-t', 'rsa', '-f', rsa_keys,
                                          '-q', '-N', '']) == 0
            print('made ssh key!')

        ssh_dir = Path(os.environ['HOME']) / '.ssh'
        ssh_dir.mkdir(exist_ok=True)

        authorized_keys = ssh_dir / 'authorized_keys'

        should_add_key = True
        if authorized_keys.exists():
            authorized_keys_data = open(os.path.join(ssh_dir, 'authorized_keys')).read()
            rsa_pkey_data = open(f'{rsa_keys}.pub').read()
            should_add_key = not rsa_pkey_data in authorized_keys_data

        if should_add_key:
            with open(os.path.join(ssh_dir, 'authorized_keys'), 'a') as ssh_file:
                with open(f'{rsa_keys}.pub') as rsa_pkey:
                    ssh_file.write('# Instance key\n')
                    ssh_file.write(rsa_pkey.read())
            print('RSA keys added')

    # pylint: disable=W0221
    def start(self, *args, **kwargs):
        self.__create_rsa_keys()
        return super().start(*args, **kwargs)

    @property
    def volumes_override(self):
        volumes = [f'{self.service_dir}/rsa_keys:/home/axonius/app/rsa_keys']
        volumes.extend(super().volumes_override)
        return volumes

    @property
    def environment(self):
        # we push here the current user to environment in order to user it for ssh
        env = super().environment
        if not env:
            env = []
        current_user = os.environ.get('SUDO_USER') or os.environ['USER']
        return env + [f'DOCKER_USER={current_user}']


@pytest.fixture(scope='module')
def image_control_fixture(request):
    service = InstanceControlService()
    initialize_fixture(request, service)
    return service
