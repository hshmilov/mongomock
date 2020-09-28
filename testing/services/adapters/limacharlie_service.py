import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class LimacharlieService(AdapterService):
    def __init__(self):
        super().__init__('limacharlie')


@pytest.fixture(scope='module', autouse=True)
def limacharlie_fixture(request):
    service = LimacharlieService()
    initialize_fixture(request, service)
    return service
