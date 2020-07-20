import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class FreeIpaService(AdapterService):
    def __init__(self):
        super().__init__('free-ipa')


@pytest.fixture(scope='module', autouse=True)
def free_ipa_fixture(request):
    service = FreeIpaService()
    initialize_fixture(request, service)
    return service
