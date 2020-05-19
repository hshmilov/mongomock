import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class HpeImcService(AdapterService):
    def __init__(self):
        super().__init__('hpe-imc')


@pytest.fixture(scope='module', autouse=True)
def hpe_imc_fixture(request):
    service = HpeImcService()
    initialize_fixture(request, service)
    return service
