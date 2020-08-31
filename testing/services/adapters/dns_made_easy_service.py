import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DnsMadeEasyService(AdapterService):
    def __init__(self):
        super().__init__('dns-made-easy')


@pytest.fixture(scope='module', autouse=True)
def dns_made_easy_fixture(request):
    service = DnsMadeEasyService()
    initialize_fixture(request, service)
    return service
