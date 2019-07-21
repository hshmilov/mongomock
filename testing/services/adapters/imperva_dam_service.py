import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ImpervaDamService(AdapterService):
    def __init__(self):
        super().__init__('imperva-dam')


@pytest.fixture(scope='module', autouse=True)
def imperva_dam_fixture(request):
    service = ImpervaDamService()
    initialize_fixture(request, service)
    return service
