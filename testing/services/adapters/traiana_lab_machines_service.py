import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TraianaLabMacinesService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__(service_dir='../adapters/traiana-lab-machines-adapter', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def traiana_lab_machines_service(request):
    service = TraianaLabMacinesService()
    initialize_fixture(request, service)
    return service
