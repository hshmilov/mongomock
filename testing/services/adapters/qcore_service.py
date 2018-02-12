import pytest

from services.plugin_service import AdapterService
from services.ports import DOCKER_PORTS
from services.simple_fixture import initialize_fixture


class QcoreService(AdapterService):
    def __init__(self):
        super().__init__('qcore')

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS[self.container_name], 80),
                (DOCKER_PORTS['qcore-mediator'], DOCKER_PORTS['qcore-mediator'])]


@pytest.fixture(scope="module", autouse=True)
def qcore_fixture(request):
    service = QcoreService()
    initialize_fixture(request, service)
    return service
