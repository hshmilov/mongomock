import subprocess

from services.docker_service import DockerService
from pathlib import Path
import json
import os
import urllib.parse


def parse_proxy(url):
    """
    :param url: proxy string as set in https_proxy. For example http://hniksic:mypassword@proxy.company.com:8001/.
    username and password are optional
    :return: parsed proxy settings
    """
    url = urllib.parse.urlparse(url)
    username = ""
    password = ""

    if '@' in url[1]:
        ident, host_port = url[1].split('@', 1)
        if ':' in ident:
            username, password = ident.split(':', 1)
        else:
            password = ident
    else:
        host_port = url[1]

    return host_port, username, password


class DiagnosticsService(DockerService):
    def is_up(self):
        return True

    def __init__(self):
        name = 'diagnostics'
        super().__init__(name, f'../devops/{name}')
        self.diag_env_file = Path(self.cortex_root_dir) / 'diag_env.json'

    def start(self, *args, **kwargs):
        if not self.diag_env_file.is_file():
            raise RuntimeError("env file is missing")
        super().start(*args, **kwargs)

    def get_dockerfile(self, mode=''):
        return ''

    def get_main_file(self):
        return ''

    @property
    def environment(self):
        env = json.loads(self.diag_env_file.read_bytes())

        proxy = env.get('HTTPS_PROXY')
        if proxy:
            connect, username, password = parse_proxy(proxy)
            yield f'PROXY_CONNECT={connect}'
            yield f'PROXY_PASSWORD={password}'
            yield f'PROXY_USERNAME={username}'
            env.pop('HTTPS_PROXY', None)

        for k, v in env.items():
            yield f'{k}={v}'

    @property
    def volumes(self):
        return [f'{self.service_dir}:/home/axonius/app']

    @property
    def exposed_ports(self):
        return []

    @property
    def docker_network(self):
        return 'host'

    def stop_async(self, **kwargs):
        assert self._process_owner, "Only process owner should be able to stop or start the fixture!"

        # just kill the ssh server
        subprocess.Popen(['docker', 'kill', self.container_name], cwd=self.service_dir,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return super().stop_async(**kwargs)
