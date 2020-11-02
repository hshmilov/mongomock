from axonius.consts.system_consts import NODE_MARKER_PATH
from services.ports import DOCKER_PORTS
from services.system_service import SystemService

HTTPD_CONTAINER_NAME = 'httpd-service'


class HttpdService(SystemService):

    def start(self, *args, **kwargs):  # pylint: disable=arguments-differ
        if NODE_MARKER_PATH.is_file():
            print(f'httpd-proxy should not run on node')
        else:
            super().start(*args, **kwargs)

    def is_up(self, *args, **kwargs):
        print(f'httpd started ok')
        return True

    def __init__(self):
        super().__init__(HTTPD_CONTAINER_NAME, service_dir='services/plugins/httpd_service')

    @staticmethod
    def port():
        return DOCKER_PORTS[HTTPD_CONTAINER_NAME]

    @property
    def volumes_override(self):
        return [f'{self.service_dir}/httpd:/usr/local/openresty/nginx/html:ro']

    @property
    def is_unique_image(self):
        return True
