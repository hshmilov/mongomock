import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class StresstestService(AdapterService):
    def __init__(self):
        super().__init__('stresstest')


@pytest.fixture(scope="module", autouse=True)
def Stresstest_fixture(request):
    service = StresstestService()
    initialize_fixture(request, service)
    return service
