import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NessusService(AdapterService):
    def __init__(self):
        super().__init__('nessus')


@pytest.fixture(scope="module", autouse=True)
def nessus_fixture(request):
    service = NessusService()
    initialize_fixture(request, service)
    return service
