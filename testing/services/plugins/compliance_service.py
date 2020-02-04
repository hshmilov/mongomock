import pytest
from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture


class ComplianceService(PluginService):
    def __init__(self):
        super().__init__('compliance')


@pytest.fixture(scope='module')
def compliance_fixture(request):
    service = ComplianceService()
    initialize_fixture(request, service)
    return service
