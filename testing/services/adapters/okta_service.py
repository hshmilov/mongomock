import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class OktaService(AdapterService):
    def __init__(self):
        super().__init__('okta')


@pytest.fixture(scope="module", autouse=True)
def okta_fixture(request):
    service = OktaService()
    initialize_fixture(request, service)
    return service
