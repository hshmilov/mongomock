import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class EnsiloService(AdapterService):
    def __init__(self):
        super().__init__('ensilo')


@pytest.fixture(scope="module", autouse=True)
def ensilo_fixture(request):
    service = EnsiloService()
    initialize_fixture(request, service)
    return service
