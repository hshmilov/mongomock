import os

import psutil

from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService
from axonius.consts.plugin_consts import LIBS_PATH

CORTEX_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

MOCKINGBIRD_SERVICE = 'mockingbird'


class MockingbirdService(WeaveService):
    def __init__(self):
        super().__init__(self.name, os.path.join('..', 'devops', MOCKINGBIRD_SERVICE))
        self.override_exposed_port = True  # if this service is up, always be exposed to remote connections

    def is_up(self, *args, **kwargs):
        return True

    @property
    def name(self):
        return MOCKINGBIRD_SERVICE

    @property
    def port(self):
        return DOCKER_PORTS[self.name]

    def get_dockerfile(self, *args, **kwargs):
        return fr'''
        FROM axonius/axonius-libs

        # Install MongoDB
        RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4 
        RUN echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/4.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-4.0.list
        RUN apt-get update && apt-get install -y mongodb-org
        
        # Create a directory for mongodb
        RUN mkdir -p /data/db

        WORKDIR /home/axonius/app
        COPY ./app ./
        COPY ./config /home/axonius/config

        # Override supervisord conf
        COPY ./config/supervisord.conf /etc/supervisor/supervisord.conf
        # uwsgi.ini is already in the correct place (config/uwsgi.ini)

        # Create a pth file to insert adapters to path
        RUN mkdir -p $(python3 -m site --user-site)
        RUN echo /home/axonius/adapters > $(python3 -m site --user-site)/axonius.pth

        '''[1:]

    def get_main_file(self):
        return ''

    @property
    def max_allowed_cpu(self):
        """
        This takes a lot of the cpu, we limit it to 25% of the machine.
        :return:
        """
        return float(round(psutil.cpu_count() / 4, 2))

    @property
    def volumes(self):
        adapters = os.path.join(CORTEX_ROOT, 'adapters')
        libs = os.path.join(CORTEX_ROOT, 'axonius-libs', 'src', 'libs')
        return [
            f'{self.container_name}_data:/data/db',
            f'{os.path.join(self.service_dir, "app")}:/home/axonius/app',
            f'{os.path.join(self.service_dir, "config")}:/home/axonius/config',
            f'{libs}:{LIBS_PATH.absolute().as_posix()}:ro',
            f'{adapters}:/home/axonius/adapters:ro'
        ]

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS[self.name], 443), (DOCKER_PORTS[self.name + '-db'], 27017)]
