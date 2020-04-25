import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class KeycloakService(AdapterService):
    def __init__(self):
        super().__init__('keycloak')


@pytest.fixture(scope='module', autouse=True)
def keycloak_fixture(request):
    service = KeycloakService()
    initialize_fixture(request, service)
    return service
