import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class HpIloService(AdapterService):
    def __init__(self):
        super().__init__('hp-ilo')


@pytest.fixture(scope='module', autouse=True)
def hp_ilo_fixture(request):
    service = HpIloService()
    initialize_fixture(request, service)
    return service
