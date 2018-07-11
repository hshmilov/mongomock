import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DuoService(AdapterService):
    def __init__(self):
        super().__init__('duo')


@pytest.fixture(scope="module", autouse=True)
def duo_fixture(request):
    service = DuoService()
    initialize_fixture(request, service)
    return service
