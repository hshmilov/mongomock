import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class OrcaService(AdapterService):
    def __init__(self):
        super().__init__('orca')


@pytest.fixture(scope='module', autouse=True)
def orca_fixture(request):
    service = OrcaService()
    initialize_fixture(request, service)
    return service
