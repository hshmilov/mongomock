import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class HaveibeenpwnedService(AdapterService):
    def __init__(self):
        super().__init__('haveibeenpwned')


@pytest.fixture(scope='module', autouse=True)
def haveibeenpwned_fixture(request):
    service = HaveibeenpwnedService()
    initialize_fixture(request, service)
    return service
