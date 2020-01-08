import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class RiskiqService(AdapterService):
    def __init__(self):
        super().__init__('riskiq')


@pytest.fixture(scope='module', autouse=True)
def riskiq_fixture(request):
    service = RiskiqService()
    initialize_fixture(request, service)
    return service
