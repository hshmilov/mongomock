import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BeyondTrustPrivilegedIdentityService(AdapterService):
    def __init__(self):
        super().__init__('beyond-trust-privileged-identity')


@pytest.fixture(scope='module', autouse=True)
def beyond_trust_privileged_identity_fixture(request):
    service = BeyondTrustPrivilegedIdentityService()
    initialize_fixture(request, service)
    return service
