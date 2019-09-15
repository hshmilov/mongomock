import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IcingaService(AdapterService):
    def __init__(self):
        super().__init__('icinga')


@pytest.fixture(scope='module', autouse=True)
def icinga_fixture(request):
    service = IcingaService()
    initialize_fixture(request, service)
    return service
