import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CitrixEpmService(AdapterService):
    def __init__(self):
        super().__init__('citrix-epm')


@pytest.fixture(scope='module', autouse=True)
def citrix_epm_fixture(request):
    service = CitrixEpmService()
    initialize_fixture(request, service)
    return service
