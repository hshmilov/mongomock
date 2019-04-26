import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SaltstackEnterpriseService(AdapterService):
    def __init__(self):
        super().__init__('saltstack-enterprise')


@pytest.fixture(scope='module', autouse=True)
def saltstack_enterprise_fixture(request):
    service = SaltstackEnterpriseService()
    initialize_fixture(request, service)
    return service
