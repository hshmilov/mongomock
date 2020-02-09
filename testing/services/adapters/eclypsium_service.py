import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class EclypsiumService(AdapterService):
    def __init__(self):
        super().__init__('eclypsium')


@pytest.fixture(scope='module', autouse=True)
def eclypsium_fixture(request):
    service = EclypsiumService()
    initialize_fixture(request, service)
    return service
