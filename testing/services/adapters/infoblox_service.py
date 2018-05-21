import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class InfobloxService(AdapterService):
    def __init__(self):
        super().__init__('infoblox')


@pytest.fixture(scope="module", autouse=True)
def infoblox_fixture(request):
    service = InfobloxService()
    initialize_fixture(request, service)
    return service
