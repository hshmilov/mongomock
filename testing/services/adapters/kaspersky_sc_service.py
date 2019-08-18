import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class KasperskyScService(AdapterService):
    def __init__(self):
        super().__init__('kaspersky-sc')


@pytest.fixture(scope='module', autouse=True)
def kaspersky_sc_fixture(request):
    service = KasperskyScService()
    initialize_fixture(request, service)
    return service
