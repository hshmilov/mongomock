import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture
from services.activateable_service import ActivateableService


class DnsConflictsService(plugin_service.PluginService, ActivateableService):
    def __init__(self, compose_file_path='../plugins/dns-conflicts-plugin/docker-compose.yml',
                 config_file_path='../plugins/dns-conflicts-plugin/src/plugin_config.ini',
                 container_name='dns-conflicts-plugin', *vargs, **kwargs):
        super().__init__(compose_file_path, config_file_path, container_name, *vargs, **kwargs)

    def find_conflicts(self):
        result = self.post('find_conflicts')
        assert result.status_code == 200
        return result


@pytest.fixture(scope="module")
def dns_conflicts_fixture(request):
    service = DnsConflictsService()
    initialize_fixture(request, service)
    return service
