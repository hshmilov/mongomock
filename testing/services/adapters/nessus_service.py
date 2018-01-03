import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NessusService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__(service_dir='../adapters/nessus-adapter', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def nessus_fixture(request):
    service = NessusService()
    initialize_fixture(request, service)
    return service
