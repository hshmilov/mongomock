# Service file
import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CentrifyService(AdapterService):
    def __init__(self):
        super().__init__('centrify')


@pytest.fixture(scope='module', autouse=True)
def centrify_fixture(request):
    service = CentrifyService()
    initialize_fixture(request, service)
    return service
