import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TaniumSqService(AdapterService):
    def __init__(self):
        super().__init__('tanium-sq')


@pytest.fixture(scope='module', autouse=True)
def tanium_sq_fixture(request):
    service = TaniumSqService()
    initialize_fixture(request, service)
    return service
