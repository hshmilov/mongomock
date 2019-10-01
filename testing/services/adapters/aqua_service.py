import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AquaService(AdapterService):
    def __init__(self):
        super().__init__('aqua')


@pytest.fixture(scope='module', autouse=True)
def aqua_fixture(request):
    service = AquaService()
    initialize_fixture(request, service)
    return service
