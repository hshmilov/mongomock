import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class InfobloxNetmriService(AdapterService):
    def __init__(self):
        super().__init__('infoblox-netmri')


@pytest.fixture(scope='module', autouse=True)
def infoblox_netmri_fixture(request):
    service = InfobloxNetmriService()
    initialize_fixture(request, service)
    return service
