import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class MobiControlService(AdapterService):
    def __init__(self):
        super().__init__('mobi-control')


@pytest.fixture(scope='module', autouse=True)
def mobi_control_fixture(request):
    service = MobiControlService()
    initialize_fixture(request, service)
    return service
