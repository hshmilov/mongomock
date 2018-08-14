import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TaniumService(AdapterService):
    def __init__(self):
        super().__init__('tanium')


@pytest.fixture(scope="module", autouse=True)
def tanium_fixture(request):
    service = TaniumService()
    initialize_fixture(request, service)
    return service
