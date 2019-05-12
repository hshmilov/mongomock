import requests

from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService
from devops.system_consts import NODE_MARKER_PATH

CONTAINER_NAME = 'master-proxy'


class MasterProxyService(WeaveService):

    def start(self, *args, **kwargs):  # pylint: disable=arguments-differ
        if NODE_MARKER_PATH.is_file():
            print(f'master-proxy should not run on node')
        else:
            super().start(*args, **kwargs)

    def is_up(self):
        try:
            response = requests.get('https://manage.chef.io',
                                    proxies={'https_proxy': f'https://127.0.0.1:{self.port()}'},
                                    timeout=(10, 60))
            if response.status_code == 200:
                print(f'proxy started ok')
            else:
                print(f'ERROR - failed to start {CONTAINER_NAME} - {response}')
        except Exception as e:
            print(f'ERROR - failed to start proxy - {e}')

        # can't let system startup fail in offline installations!
        return True

    def __init__(self):
        super().__init__(CONTAINER_NAME, service_dir='services/standalone_services')

    @staticmethod
    def port():
        return DOCKER_PORTS[CONTAINER_NAME]

    @property
    def exposed_ports(self):
        return [(self.port(), self.port())]

    @property
    def volumes(self):
        return []

    @property
    def volumes_override(self):
        return []
