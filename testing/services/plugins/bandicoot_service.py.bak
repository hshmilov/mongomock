from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService


class BandicootService(WeaveService):
    """
    Postgres service docker definition
    """

    def __init__(self):
        super().__init__('bandicoot', '../bandicoot')

    @property
    def exposed_ports(self):
        """
         :return: list of pairs (exposed_port, inner_port)
        """
        return [(DOCKER_PORTS[self.container_name], 9090)]

    @property
    def _additional_parameters(self):
        return ['api',  '--mgHostname=mongo.axonius.local', '--pgHostname=postgres.axonius.local', '--pgPort=5432',
                '--verbose=true',  '--apiAddr=0.0.0.0', '--logDirectory=/home/axonius/logs',
                '--apiSSLCert=/etc/ssl/certs/nginx-selfsigned.crt', '--apiSSLKey=/etc/ssl/private/nginx-selfsigned.key']

    def get_dockerfile(self, *args, **kwargs):
        with open('../bandicoot/Dockerfile') as f:
            return f.read()

    @property
    def is_unique_image(self):
        return True

    def remove_image(self):
        pass  # We never want to remove this static image...

    def is_up(self, *args, **kwargs):
        return self.get_is_container_up()
