import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ZoomService(AdapterService):
    def __init__(self):
        super().__init__('zoom')


@pytest.fixture(scope='module', autouse=True)
def zoom_fixture(request):
    service = ZoomService()
    initialize_fixture(request, service)
    return service
