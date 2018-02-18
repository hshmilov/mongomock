import pytest

from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture
from services.activateable_service import ActivateableService


class GeneralInfoService(PluginService, ActivateableService):
    def __init__(self):
        super().__init__('general-info')

    def run(self):
        result = self.post('run')
        assert result.status_code == 200
        return result


@pytest.fixture(scope="module")
def general_info_fixture(request):
    service = GeneralInfoService()
    initialize_fixture(request, service)
    return service
