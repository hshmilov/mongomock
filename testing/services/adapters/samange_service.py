import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SamangeService(AdapterService):
    def __init__(self):
        super().__init__('samange')


@pytest.fixture(scope='module', autouse=True)
def samange_fixture(request):
    service = SamangeService()
    initialize_fixture(request, service)
    return service
