import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ObserveitService(AdapterService):
    def __init__(self):
        super().__init__('observeit')


@pytest.fixture(scope="module", autouse=True)
def observeit_fixture(request):
    service = ObserveitService()
    initialize_fixture(request, service)
    return service
