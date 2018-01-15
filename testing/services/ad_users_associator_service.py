import pytest

from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture
from services.activateable_service import ActivateableService


class AdUsersAssociatorService(PluginService, ActivateableService):
    def __init__(self, **kwargs):
        super().__init__(service_dir='../plugins/ad-users-associator-plugin', **kwargs)

    def associate(self):
        result = self.post('associate')
        assert result.status_code == 200
        return result


@pytest.fixture(scope="module")
def ad_users_associator_fixture(request):
    service = AdUsersAssociatorService()
    initialize_fixture(request, service)
    return service
