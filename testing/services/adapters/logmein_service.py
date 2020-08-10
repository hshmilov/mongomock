import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class LogmeinService(AdapterService):
    def __init__(self):
        super().__init__('logmein')


@pytest.fixture(scope='module', autouse=True)
def logmein_fixture(request):
    service = LogmeinService()
    initialize_fixture(request, service)
    return service
