import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ForcepointService(AdapterService):
    def __init__(self):
        super().__init__('forcepoint')


@pytest.fixture(scope='module', autouse=True)
def forcepoint_fixture(request):
    service = ForcepointService()
    initialize_fixture(request, service)
    return service
