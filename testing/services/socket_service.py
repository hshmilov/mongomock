import services.compose_service as compose_service
import requests
import services.compose_parser


class SocketService(compose_service.ComposeService):
    def __init__(self, compose_file_path):
        super().__init__(compose_file_path)
        self.parsed_compose_file = services.compose_parser.ServiceYmlParser(compose_file_path)
        port = self.parsed_compose_file.exposed_port
        self.endpoint = ('localhost', port)

    @staticmethod
    def is_endpoint_alive(endpoint):
        try:
            r = requests.get("http://%s:%s/version" % (endpoint[0], endpoint[1]))
            return r.status_code == 200
        except:
            return False

    def is_up(self):
        return self.is_endpoint_alive(self.endpoint)
