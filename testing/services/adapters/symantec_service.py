import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SymantecService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__('symantec', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def symantec_fixture(request):
    service = SymantecService()
    initialize_fixture(request, service)
    return service
