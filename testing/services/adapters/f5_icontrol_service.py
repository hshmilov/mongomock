import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class F5IcontrolService(AdapterService):
    def __init__(self):
        super().__init__('f5-icontrol')


@pytest.fixture(scope='module', autouse=True)
def f5_icontrol_fixture(request):
    service = F5IcontrolService()
    initialize_fixture(request, service)
    return service
