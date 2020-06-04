import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AlcideService(AdapterService):
    def __init__(self):
        super().__init__('alcide')


@pytest.fixture(scope='module', autouse=True)
def alcide_fixture(request):
    service = AlcideService()
    initialize_fixture(request, service)
    return service
