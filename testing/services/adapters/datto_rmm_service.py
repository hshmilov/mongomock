import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DattoRmmService(AdapterService):
    def __init__(self):
        super().__init__('datto-rmm')


@pytest.fixture(scope='module', autouse=True)
def datto_rmm_fixture(request):
    service = DattoRmmService()
    initialize_fixture(request, service)
    return service
