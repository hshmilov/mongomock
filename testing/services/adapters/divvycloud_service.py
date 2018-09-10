import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DivvycloudService(AdapterService):
    def __init__(self):
        super().__init__('divvycloud')


@pytest.fixture(scope='module', autouse=True)
def divvycloud_fixture(request):
    service = DivvycloudService()
    initialize_fixture(request, service)
    return service
