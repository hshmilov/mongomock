import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class WebrootService(AdapterService):
    def __init__(self):
        super().__init__('webroot')


@pytest.fixture(scope='module', autouse=True)
def webroot_fixture(request):
    service = WebrootService()
    initialize_fixture(request, service)
    return service
