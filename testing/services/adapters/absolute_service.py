import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AbsoluteService(AdapterService):
    def __init__(self):
        super().__init__('absolute')


@pytest.fixture(scope='module', autouse=True)
def absolute_fixture(request):
    service = AbsoluteService()
    initialize_fixture(request, service)
    return service
