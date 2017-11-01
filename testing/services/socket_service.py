import services.compose_service as compose_service
import socket


class SocketService(compose_service.ComposeService):
    def __init__(self, endpoint, config_file_path):
        super().__init__(config_file_path)
        self.endpoint = endpoint

    @staticmethod
    def is_socket_alive(endpoit):
        try:
            socket.create_connection(endpoit)
            return True
        except:
            return False

    def is_up(self):
        return self.is_socket_alive(self.endpoint)
