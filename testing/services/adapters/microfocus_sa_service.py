import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class MicrofocusSaService(AdapterService):
    def __init__(self):
        super().__init__('microfocus-sa')


@pytest.fixture(scope='module', autouse=True)
def microfocus_sa_fixture(request):
    service = MicrofocusSaService()
    initialize_fixture(request, service)
    return service
