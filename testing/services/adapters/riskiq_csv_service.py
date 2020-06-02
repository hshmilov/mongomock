import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class RiskiqCsvService(AdapterService):
    def __init__(self):
        super().__init__('riskiq-csv')


@pytest.fixture(scope='module', autouse=True)
def riskiq_csv_fixture(request):
    service = RiskiqCsvService()
    initialize_fixture(request, service)
    return service
