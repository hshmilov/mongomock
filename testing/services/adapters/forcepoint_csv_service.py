import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ForcepointCsvService(AdapterService):
    def __init__(self):
        super().__init__('forcepoint-csv')


@pytest.fixture(scope="module", autouse=True)
def forcepoint_csv_fixture(request):
    service = ForcepointCsvService()
    initialize_fixture(request, service)
    return service
