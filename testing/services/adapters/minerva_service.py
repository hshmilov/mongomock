import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class MinervaService(AdapterService):
    def __init__(self):
        super().__init__('minerva')


@pytest.fixture(scope="module", autouse=True)
def minerva_fixture(request):
    service = MinervaService()
    initialize_fixture(request, service)
    return service
