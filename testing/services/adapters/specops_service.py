import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SpecopsService(AdapterService):
    def __init__(self):
        super().__init__('specops')


@pytest.fixture(scope='module', autouse=True)
def specops_fixture(request):
    service = SpecopsService()
    initialize_fixture(request, service)
    return service
