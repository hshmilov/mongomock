import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DruvaService(AdapterService):
    def __init__(self):
        super().__init__('druva')


@pytest.fixture(scope='module', autouse=True)
def druva_fixture(request):
    service = DruvaService()
    initialize_fixture(request, service)
    return service
