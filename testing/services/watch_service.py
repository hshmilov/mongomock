import pytest

from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture


class WatchService(PluginService):
    def __init__(self, **kwargs):
        super().__init__('watch-service', service_dir='../plugins/watch-service', **kwargs)

    def _request_watches(self, method, *vargs, **kwargs):
        return getattr(self, method)('watch', api_key=self.api_key, *vargs, **kwargs)

    def get_watches(self, *vargs, **kwargs):
        return self._request_watches('get', *vargs, **kwargs)

    def create_watch(self, data, *vargs, **kwargs):
        return self._request_watches('put', data=data, *vargs, **kwargs)

    def delete_watch(self, data, *vargs, **kwargs):
        return self._request_watches('delete', data=data, *vargs, **kwargs)

    def run_jobs(self):
        self.get('trigger_watches', api_key=self.api_key)


@pytest.fixture(scope="module")
def watch_fixture(request):
    service = WatchService()
    initialize_fixture(request, service)
    return service
