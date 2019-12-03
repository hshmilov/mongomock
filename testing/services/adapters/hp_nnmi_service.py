import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class HpNnmiService(AdapterService):
    def __init__(self):
        super().__init__('hp-nnmi')


@pytest.fixture(scope='module', autouse=True)
def hp_nnmi_fixture(request):
    service = HpNnmiService()
    initialize_fixture(request, service)
    return service
