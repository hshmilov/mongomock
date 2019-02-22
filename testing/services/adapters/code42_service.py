import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class Code42Service(AdapterService):
    def __init__(self):
        super().__init__('code42')


@pytest.fixture(scope='module', autouse=True)
def code42_fixture(request):
    service = Code42Service()
    initialize_fixture(request, service)
    return service
