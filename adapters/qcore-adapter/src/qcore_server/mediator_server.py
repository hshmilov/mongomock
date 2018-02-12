import socketserver

from protocol.exceptions import ProtocolException
from protocol.qtp.qtp_message import QtpMessage
from qcore_server.pump_connection import PumpConnection


class MyTCPHandler(socketserver.StreamRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def send_and_flush(self, bytes):
        self.wfile.write(bytes)
        self.wfile.flush()

    def get_send_func(self):
        def send_func(bytes):
            self.send_and_flush(bytes)

        return send_func

    def handle(self):

        print(f"Established connection {self.client_address}")

        pump_connection = PumpConnection(self.get_send_func())

        connection_alive = False
        while not connection_alive:
            qtp = QtpMessage()

            try:

                while not qtp.is_complete():
                    inp = self.rfile.read(qtp.remaining_bytes())
                    if len(inp) == 0:
                        print("DONE...")
                        connection_alive = True
                        break

                    qtp.extend_bytes(inp)

                pump_connection.on_message(qtp)
            except ProtocolException:
                pass


def run_mediator_server():
    host, port = '0.0.0.0', 5016
    socketserver.TCPServer.allow_reuse_address = True
    # Create the server, binding to localhost on port 9999
    with socketserver.TCPServer((host, port), MyTCPHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()


if __name__ == "__main__":
    run_mediator_server()
