import pytest
import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture


class AdService(plugin_service.AdapterService):
    def __init__(self, compose_file_path='../adapters/ad-adapter/docker-compose.yml',
                 config_file_path='../adapters/ad-adapter/src/plugin_config.ini',
                 container_name="ad-adapter",
                 *vargs, **kwargs):
        super().__init__(compose_file_path, config_file_path, container_name, *vargs, **kwargs)

    def resolve_ip(self):
        self.post('resolve_ip', None, None)


@pytest.fixture(scope="module", autouse=True)
def ad_fixture(request):
    service = AdService()
    initialize_fixture(request, service)
    return service
