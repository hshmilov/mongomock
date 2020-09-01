import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NasuniService(AdapterService):
    def __init__(self):
        super().__init__('nasuni')


@pytest.fixture(scope='module', autouse=True)
def nasuni_fixture(request):
    service = NasuniService()
    initialize_fixture(request, service)
    return service
