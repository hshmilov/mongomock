import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IntrigueService(AdapterService):
    def __init__(self):
        super().__init__('intrigue')


@pytest.fixture(scope='module', autouse=True)
def intrigue_fixture(request):
    service = IntrigueService()
    initialize_fixture(request, service)
    return service
