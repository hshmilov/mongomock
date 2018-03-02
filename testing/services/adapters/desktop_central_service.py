import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DesktopCentralService(AdapterService):
    def __init__(self):
        super().__init__('desktop-central')


@pytest.fixture(scope="module", autouse=True)
def desktop_central_fixture(request):
    service = DesktopCentralService()
    initialize_fixture(request, service)
    return service
