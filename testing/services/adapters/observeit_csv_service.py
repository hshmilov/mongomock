import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ObserveitCsvService(AdapterService):
    def __init__(self):
        super().__init__('observeit-csv')


@pytest.fixture(scope="module", autouse=True)
def observeit_csv_fixture(request):
    service = ObserveitCsvService()
    initialize_fixture(request, service)
    return service
