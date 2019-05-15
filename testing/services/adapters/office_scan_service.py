import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class OfficeScanService(AdapterService):
    def __init__(self):
        super().__init__('office-scan')


@pytest.fixture(scope='module', autouse=True)
def office_scan_fixture(request):
    service = OfficeScanService()
    initialize_fixture(request, service)
    return service
