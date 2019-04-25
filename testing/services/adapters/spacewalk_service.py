import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SpacewalkService(AdapterService):
    def __init__(self):
        super().__init__('spacewalk')


@pytest.fixture(scope='module', autouse=True)
def spacewalk_fixture(request):
    service = SpacewalkService()
    initialize_fixture(request, service)
    return service
