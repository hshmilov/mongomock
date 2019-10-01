import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SymantecDlpService(AdapterService):
    def __init__(self):
        super().__init__('symantec-dlp')


@pytest.fixture(scope='module', autouse=True)
def symantec_dlp_fixture(request):
    service = SymantecDlpService()
    initialize_fixture(request, service)
    return service
