import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TraianaLabMachinesService(AdapterService):
    def __init__(self):
        super().__init__('traiana-lab-machines')


@pytest.fixture(scope="module", autouse=True)
def traiana_lab_machines_service(request):
    service = TraianaLabMachinesService()
    initialize_fixture(request, service)
    return service
