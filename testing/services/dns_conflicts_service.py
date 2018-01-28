import pytest

from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture
from services.activateable_service import ActivateableService


class DnsConflictsService(PluginService, ActivateableService):
    def __init__(self, **kwargs):
        super().__init__('dns-conflicts-plugin', service_dir='../plugins/dns-conflicts-plugin', **kwargs)

    def find_conflicts(self):
        result = self.post('find_conflicts')
        assert result.status_code == 200
        return result


@pytest.fixture(scope="module")
def dns_conflicts_fixture(request):
    service = DnsConflictsService()
    initialize_fixture(request, service)
    return service
