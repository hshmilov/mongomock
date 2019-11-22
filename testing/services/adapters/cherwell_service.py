import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CherwellService(AdapterService):
    def __init__(self):
        super().__init__('cherwell')


@pytest.fixture(scope='module', autouse=True)
def cherwell_fixture(request):
    service = CherwellService()
    initialize_fixture(request, service)
    return service
