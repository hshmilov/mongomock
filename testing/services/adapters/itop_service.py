import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ItopService(AdapterService):
    def __init__(self):
        super().__init__('itop')


@pytest.fixture(scope='module', autouse=True)
def itop_fixture(request):
    service = ItopService()
    initialize_fixture(request, service)
    return service
