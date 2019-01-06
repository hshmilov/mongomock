import os
from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService


class MockingbirdService(WeaveService):
    def __init__(self):
        super().__init__(self.name, os.path.join('..', 'devops', 'mockingbird'))
        self.override_exposed_port = True   # if this service is up, always be exposed to remote connections

    def is_up(self):
        return True

    @property
    def name(self):
        return 'mockingbird'

    @property
    def port(self):
        return DOCKER_PORTS[self.name]

    def get_dockerfile(self, mode=''):
        return fr'''
        FROM tiangolo/uwsgi-nginx-flask:python3.7
        # If STATIC_INDEX is 1, serve / with /static/index.html directly (or the static URL configured)
        ENV STATIC_INDEX 1
        # ENV STATIC_INDEX 0

        # Install MongoDB
        RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4 
        RUN echo "deb http://repo.mongodb.org/apt/debian stretch/mongodb-org/4.0 main" | tee "/etc/apt/sources.list.d/mongodb-org-4.0.list"
        RUN apt-get update && apt-get install -y mongodb-org

        COPY ./app /app
        RUN pip install -r /app/requirements.txt
        '''[1:]

    def get_main_file(self):
        return ''

    @property
    def volumes(self):
        return [f'{os.path.join(self.service_dir, "app")}:/app']

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS[self.name], 80)]
