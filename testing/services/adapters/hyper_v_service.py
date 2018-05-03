import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class HyperVService(AdapterService):
    def __init__(self):
        super().__init__('hyper-v')


@pytest.fixture(scope="module", autouse=True)
def hyper_v_fixture(request):
    service = HyperVService()
    initialize_fixture(request, service)
    return service
