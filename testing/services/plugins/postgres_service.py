from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService


class PostgresService(WeaveService):
    """
    Postgres service docker definition
    """

    def __init__(self):
        super().__init__('postgres', '../bandicoot/deployments/docker/postgres')

    @property
    def exposed_ports(self):
        """
        :return: list of pairs (exposed_port, inner_port)
        """
        return [(DOCKER_PORTS[self.container_name], 5432)]

    @property
    def environment(self):
        return ['POSTGRES_USER=postgres',
                'POSTGRES_PASSWORD=changeme',
                'PG_SYSTEM_SHARED_BUFFERS=2GB']

    def get_uwsgi_file(self):
        return ''

    def get_dockerfile(self, *args, **kwargs):
        with open('../bandicoot/deployments/docker/postgres/Dockerfile') as f:
            return f.read()

    @property
    def image(self):
        return 'axonius_postgres'

    def get_main_file(self):
        return ''

    @property
    def volumes(self):
        return [f'{self.container_name}_data:/var/lib/postgresql/data']

    def remove_image(self):
        pass  # We never want to remove this static image...

    def is_up(self, *args, **kwargs):
        return True
