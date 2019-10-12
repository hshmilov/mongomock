import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BamboohrService(AdapterService):
    def __init__(self):
        super().__init__('bamboohr')


@pytest.fixture(scope='module', autouse=True)
def bamboohr_fixture(request):
    service = BamboohrService()
    initialize_fixture(request, service)
    return service
