import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class HashicorpService(AdapterService):
    def __init__(self):
        super().__init__('hashicorp')


@pytest.fixture(scope='module', autouse=True)
def hashicorp_fixture(request):
    service = HashicorpService()
    initialize_fixture(request, service)
    return service
