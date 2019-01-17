import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ForemanService(AdapterService):
    def __init__(self):
        super().__init__('foreman')


@pytest.fixture(scope='module', autouse=True)
def foreman_fixture(request):
    service = ForemanService()
    initialize_fixture(request, service)
    return service
