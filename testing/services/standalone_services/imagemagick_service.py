import os
import shlex

from axonius.consts.system_consts import STANDALONE_NETWORK
from services.docker_service import DockerService


class ImagemagickService(DockerService):

    def __init__(self):
        super().__init__(self.name, '')
        self.parameters = []

    @property
    def name(self):
        return 'imagemagick'

    @property
    def docker_network(self):
        return STANDALONE_NETWORK

    @property
    def _additional_parameters(self):
        return self.parameters

    def get_dockerfile(self, *args, **kwargs):
        return r'''
        FROM alpine:3.11.6

        RUN apk add --update imagemagick curl

        ENTRYPOINT ["convert"]
        '''[1:]

    @property
    def is_unique_image(self):
        return True

    def remove_image(self):
        pass  # We never want to remove this static image...

    def is_up(self, *args, **kwargs):
        return self.get_is_container_up()

    def _get_env_varaibles(self, docker_internal_env_vars, mode):
        return []

    def _get_volumes(self):
        return ['-v', self.parameters.pop(0)]

    def _get_allowed_memory(self):
        return []

    def _get_allowed_cpu(self):
        return []

    def _get_exposed_ports(self, mode, expose_port):
        return []

    @staticmethod
    def _remove_container_when_exit():
        return True

    def start(self, *args, **kwargs):  # pylint: disable=arguments-differ
        env_service_dir = os.environ.get('SERVICE_DIR', '/home/ubuntu/cortex')
        env_variables = kwargs.get('docker_internal_env_vars')
        print(kwargs)
        image_folder = f'{shlex.quote(env_variables[0].replace("image_folder=", ""))}:/imgs'
        image_folder = image_folder.replace('/home/ubuntu/cortex', env_service_dir)
        source = shlex.quote(f'/imgs/{env_variables[1].replace("source=", "")}')
        destination = shlex.quote(f'/imgs/{env_variables[2].replace("target=", "")}')
        if not source or not destination:
            print(f'{self.container_name} should not run without the source and destination.')
            return
        self.parameters.clear()
        self.parameters.append(image_folder)
        self.parameters.append(source)
        self.parameters.append(destination)

        super().start(*args, **kwargs)
