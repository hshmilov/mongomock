import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BeyondTrustService(AdapterService):
    def __init__(self):
        super().__init__('beyond-trust')


@pytest.fixture(scope='module', autouse=True)
def beyond_trust_fixture(request):
    service = BeyondTrustService()
    initialize_fixture(request, service)
    return service
