import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CiscoFirepowerManagementCenterService(AdapterService):
    def __init__(self):
        super().__init__('cisco-firepower-management-center')


@pytest.fixture(scope='module', autouse=True)
def cisco_firepower_management_center_fixture(request):
    service = CiscoFirepowerManagementCenterService()
    initialize_fixture(request, service)
    return service
