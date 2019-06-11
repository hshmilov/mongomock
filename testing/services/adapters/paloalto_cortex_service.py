import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PaloaltoCortexService(AdapterService):
    def __init__(self):
        super().__init__('paloalto-cortex')


@pytest.fixture(scope='module', autouse=True)
def paloalto_cortex_fixture(request):
    service = PaloaltoCortexService()
    initialize_fixture(request, service)
    return service
