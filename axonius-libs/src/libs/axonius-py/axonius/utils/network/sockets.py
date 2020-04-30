import logging
import socket


logger = logging.getLogger(f'axonius.{__name__}')


def test_reachability_tcp(host, port, timeout=10):
    sock = None
    try:
        port = int(port)
    except Exception:
        logger.exception(f'Test reachability for {host}:{port} error: Invalid port {port}')
        return False

    try:
        sock = socket.create_connection((host, int(port)), timeout)
        return True
    except Exception as e:
        logger.exception(f'Test reachability for {host}:{port} error: {str(e)}')
        return False
    finally:
        try:
            if sock:
                sock.close()
        except Exception:
            pass
