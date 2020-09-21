import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ThycoticService(AdapterService):
    def __init__(self):
        super().__init__('thycotic')


@pytest.fixture(scope='module', autouse=True)
def thycotic_fixture(request):
    service = ThycoticService()
    initialize_fixture(request, service)
    return service
