import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class KennaService(AdapterService):
    def __init__(self):
        super().__init__('kenna')


@pytest.fixture(scope='module', autouse=True)
def kenna_fixture(request):
    service = KennaService()
    initialize_fixture(request, service)
    return service
