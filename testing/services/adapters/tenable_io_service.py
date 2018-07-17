import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TenableIoService(AdapterService):
    def __init__(self):
        super().__init__('tenable-io')


@pytest.fixture(scope="module", autouse=True)
def tenable_io_fixture(request):
    service = TenableIoService()
    initialize_fixture(request, service)
    return service
