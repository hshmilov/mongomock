import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class StresstestScannerService(AdapterService):
    def __init__(self):
        super().__init__('stresstest-scanner')


@pytest.fixture(scope="module", autouse=True)
def StresstestScanner_fixture(request):
    service = StresstestScannerService()
    initialize_fixture(request, service)
    return service
