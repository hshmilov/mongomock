import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class EdgescanService(AdapterService):
    def __init__(self):
        super().__init__('edgescan')


@pytest.fixture(scope='module', autouse=True)
def edgescan_fixture(request):
    service = EdgescanService()
    initialize_fixture(request, service)
    return service
