import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IvantiSmService(AdapterService):
    def __init__(self):
        super().__init__('ivanti-sm')


@pytest.fixture(scope='module', autouse=True)
def ivanti_sm_fixture(request):
    service = IvantiSmService()
    initialize_fixture(request, service)
    return service
