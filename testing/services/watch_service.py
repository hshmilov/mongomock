import pytest
import json

import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture


class WatchService(plugin_service.PluginService):
    def __init__(self, compose_file_path='../plugins/watch-service/docker-compose.yml',
                 config_file_path='../plugins/watch-service/src/plugin_config.ini',
                 container_name='watch-service', *vargs, **kwargs):
        super().__init__(compose_file_path, config_file_path, container_name, *vargs, **kwargs)

    def _request_watches(self, method, *kargs, **kwargs):
        return getattr(self, method)('watch', api_key=self.api_key, *kargs, **kwargs)

    def get_watches(self, *kargs, **kwargs):
        return self._request_watches('get', *kargs, **kwargs)

    def create_watch(self, data, *kargs, **kwargs):
        return self._request_watches('put', data=data, *kargs, **kwargs)

    def delete_watch(self, data, *kargs, **kwargs):
        return self._request_watches('delete', data=data, *kargs, **kwargs)

    def run_jobs(self):
        self.get('trigger_watches', api_key=self.api_key)


@pytest.fixture(scope="module")
def watch_fixture(request):
    service = WatchService()
    initialize_fixture(request, service)
    return service
