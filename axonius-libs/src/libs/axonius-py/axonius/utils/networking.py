import logging
import socket

logger = logging.getLogger(f'axonius.{__name__}')


def check_if_tcp_port_is_open(address: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(10)
        result = sock.connect_ex((address, int(port)))
        if result:
            logger.warning(f'Checking if port {port} is open on {address!r}: error code {result}')
        return result == 0
    except Exception:
        logger.warning(f'Warning - could not check if tcp port open for {address!r} and port {port}', exc_info=True)
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass
