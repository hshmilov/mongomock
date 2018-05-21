import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SymantecAltirisService(AdapterService):
    def __init__(self):
        super().__init__('symantec-altiris')


@pytest.fixture(scope="module", autouse=True)
def symantec_altiris_fixture(request):
    service = SymantecAltirisService()
    initialize_fixture(request, service)
    return service
