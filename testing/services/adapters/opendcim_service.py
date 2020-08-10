import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class OpendcimService(AdapterService):
    def __init__(self):
        super().__init__('opendcim')


@pytest.fixture(scope='module', autouse=True)
def opendcim_fixture(request):
    service = OpendcimService()
    initialize_fixture(request, service)
    return service
