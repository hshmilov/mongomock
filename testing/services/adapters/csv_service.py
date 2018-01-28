import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CsvService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__('csv', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def csv_fixture(request):
    service = CsvService()
    initialize_fixture(request, service)
    return service
