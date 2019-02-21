import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ArmisService(AdapterService):
    def __init__(self):
        super().__init__('armis')


@pytest.fixture(scope='module', autouse=True)
def armis_fixture(request):
    service = ArmisService()
    initialize_fixture(request, service)
    return service
