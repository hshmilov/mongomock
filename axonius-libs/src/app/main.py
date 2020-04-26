# Identify the adapter/service we are running and import it for uwsgi.
# pylint: disable=invalid-name
import importlib
import os

from axonius.utils.server import init_wsgi


current_service = getattr(importlib.import_module(f'{os.environ["PACKAGE_NAME"]}.service'),
                          os.environ['SERVICE_CLASS_NAME'])

if __name__ == '__main__':
    # Initialize
    service = current_service()

    # Run (Blocking)
    service.start_serve()
else:
    # Init wsgi if in it.
    wsgi_app = init_wsgi(current_service)
