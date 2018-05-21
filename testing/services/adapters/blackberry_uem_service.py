import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BlackberryUemService(AdapterService):
    def __init__(self):
        super().__init__('blackberry-uem')


@pytest.fixture(scope="module", autouse=True)
def blackberry_uem_fixture(request):
    service = BlackberryUemService()
    initialize_fixture(request, service)
    return service
