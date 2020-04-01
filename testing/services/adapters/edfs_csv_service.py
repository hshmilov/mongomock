import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class EdfsCsvService(AdapterService):
    def __init__(self):
        super().__init__('edfs-csv')


@pytest.fixture(scope='module', autouse=True)
def edfs_csv_fixture(request):
    service = EdfsCsvService()
    initialize_fixture(request, service)
    return service
