import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SccmService(AdapterService):
    def __init__(self):
        super().__init__('sccm')


@pytest.fixture(scope="module", autouse=True)
def sccm_fixture(request):
    service = SccmService()
    initialize_fixture(request, service)
    return service
