import socketserver
import threading

from qcore_adapter.protocol.exceptions import ProtocolException
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage
from qcore_adapter.server.pump_connection import PumpConnection


class MyTCPHandler(socketserver.StreamRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):

        send_lock = threading.Lock()

        def send_and_flush(bytes_to_send):
            with send_lock:
                self.wfile.write(bytes_to_send)
                self.wfile.flush()

        print(f'Connection established: {self.client_address}')

        pump_connection = PumpConnection(send_and_flush)

        connection_alive = False
        while not connection_alive:
            qtp = QtpMessage()

            while not qtp.is_complete():
                inp = self.rfile.read(qtp.remaining_bytes())
                if len(inp) == 0:
                    print(f'Connection lost: {self.client_address}')
                    connection_alive = True
                    break

                qtp.extend_bytes(inp)

            pump_connection.on_message(qtp)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def run_mediator_server():
    host, port = '0.0.0.0', 5016
    socketserver.TCPServer.allow_reuse_address = True
    # Create the server, binding to address
    with ThreadedTCPServer((host, port), MyTCPHandler) as server:
        # Activate the server
        while 1:
            server.serve_forever()


if __name__ == "__main__":
    run_mediator_server()
