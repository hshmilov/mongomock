import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IndegyService(AdapterService):
    def __init__(self):
        super().__init__('indegy')


@pytest.fixture(scope='module', autouse=True)
def indegy_fixture(request):
    service = IndegyService()
    initialize_fixture(request, service)
    return service
