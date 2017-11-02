import services.compose_service as compose_service
import requests


class SocketService(compose_service.ComposeService):
    def __init__(self, endpoint, config_file_path):
        super().__init__(config_file_path)
        self.endpoint = endpoint

    @staticmethod
    def is_endpoint_alive(endpoint):
        try:
            r = requests.get("http://%s:%s/version" % (endpoint[0], endpoint[1]))
            return r.status_code == 200
        except:
            return False

    def is_up(self):
        return self.is_endpoint_alive(self.endpoint)
