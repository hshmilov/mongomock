import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NessusCsvService(AdapterService):
    def __init__(self):
        super().__init__('nessus-csv')


@pytest.fixture(scope="module", autouse=True)
def nessus_csv_fixture(request):
    service = NessusCsvService()
    initialize_fixture(request, service)
    return service
