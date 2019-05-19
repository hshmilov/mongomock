import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class LibrenmsService(AdapterService):
    def __init__(self):
        super().__init__('librenms')


@pytest.fixture(scope='module', autouse=True)
def librenms_fixture(request):
    service = LibrenmsService()
    initialize_fixture(request, service)
    return service
