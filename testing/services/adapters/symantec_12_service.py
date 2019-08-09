import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class Symantec12Service(AdapterService):
    def __init__(self):
        super().__init__('symantec-12')


@pytest.fixture(scope='module', autouse=True)
def symantec_12_fixture(request):
    service = Symantec12Service()
    initialize_fixture(request, service)
    return service
