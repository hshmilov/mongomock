import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class Knowbe4Service(AdapterService):
    def __init__(self):
        super().__init__('knowbe4')


@pytest.fixture(scope='module', autouse=True)
def knowbe4_fixture(request):
    service = Knowbe4Service()
    initialize_fixture(request, service)
    return service
