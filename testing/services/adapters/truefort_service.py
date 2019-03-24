import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TruefortService(AdapterService):
    def __init__(self):
        super().__init__('truefort')


@pytest.fixture(scope='module', autouse=True)
def truefort_fixture(request):
    service = TruefortService()
    initialize_fixture(request, service)
    return service
