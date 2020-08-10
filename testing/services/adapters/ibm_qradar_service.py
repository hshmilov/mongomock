import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IbmQradarService(AdapterService):
    def __init__(self):
        super().__init__('ibm-qradar')


@pytest.fixture(scope='module', autouse=True)
def ibm_qradar_fixture(request):
    service = IbmQradarService()
    initialize_fixture(request, service)
    return service
