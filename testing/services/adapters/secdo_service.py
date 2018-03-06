import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SecdoService(AdapterService):
    def __init__(self):
        super().__init__('secdo')


@pytest.fixture(scope="module", autouse=True)
def secdo_fixture(request):
    service = SecdoService()
    initialize_fixture(request, service)
    return service
