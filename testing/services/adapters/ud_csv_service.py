import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class UdCsvService(AdapterService):
    def __init__(self):
        super().__init__('ud-csv')


@pytest.fixture(scope='module', autouse=True)
def ud_csv_fixture(request):
    service = UdCsvService()
    initialize_fixture(request, service)
    return service
