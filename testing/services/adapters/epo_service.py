import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class EpoService(AdapterService):
    def __init__(self):
        super().__init__('epo')


@pytest.fixture(scope="module", autouse=True)
def epo_fixture(request):
    service = EpoService()
    initialize_fixture(request, service)
    return service
