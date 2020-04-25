import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BoxPlatformService(AdapterService):
    def __init__(self):
        super().__init__('box-platform')


@pytest.fixture(scope='module', autouse=True)
def box_platform_fixture(request):
    service = BoxPlatformService()
    initialize_fixture(request, service)
    return service
