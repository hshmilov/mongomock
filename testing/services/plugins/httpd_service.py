from axonius.consts.system_consts import NODE_MARKER_PATH
from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService

HTTPD_CONTAINER_NAME = 'httpd-service'


class HttpdService(WeaveService):

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
        return [f'{self.service_dir}/httpd:/usr/share/nginx/html:ro']

    def get_main_file(self):
        return ''

    def get_uwsgi_file(self):
        return ''
