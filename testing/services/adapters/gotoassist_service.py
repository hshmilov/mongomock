import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class GotoassistService(AdapterService):
    def __init__(self):
        super().__init__('gotoassist')


@pytest.fixture(scope="module", autouse=True)
def gotoassist_fixture(request):
    service = GotoassistService()
    initialize_fixture(request, service)
    return service
