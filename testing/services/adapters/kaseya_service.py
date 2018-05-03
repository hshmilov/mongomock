import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class KaseyaService(AdapterService):
    def __init__(self):
        super().__init__('kaseya')


@pytest.fixture(scope="module", autouse=True)
def kaseya_fixture(request):
    service = KaseyaService()
    initialize_fixture(request, service)
    return service
