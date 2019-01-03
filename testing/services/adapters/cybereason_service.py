import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CybereasonService(AdapterService):
    def __init__(self):
        super().__init__('cybereason')


@pytest.fixture(scope='module', autouse=True)
def cybereason_fixture(request):
    service = CybereasonService()
    initialize_fixture(request, service)
    return service
