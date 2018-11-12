import pytest
from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TripwireEnterpriseService(AdapterService):
    def __init__(self):
        super().__init__('tripwire-enterprise')


@pytest.fixture(scope='module', autouse=True)
def tripwire_enterprise_fixture(request):
    service = TripwireEnterpriseService()
    initialize_fixture(request, service)
    return service
