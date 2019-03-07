import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DynatraceService(AdapterService):
    def __init__(self):
        super().__init__('dynatrace')


@pytest.fixture(scope='module', autouse=True)
def dynatrace_fixture(request):
    service = DynatraceService()
    initialize_fixture(request, service)
    return service
