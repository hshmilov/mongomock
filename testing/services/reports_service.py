from services.plugin_service import PluginService


class ReportsService(PluginService):
    def __init__(self):
        super().__init__('reports')

    def _request_watches(self, method, *vargs, **kwargs):
        return getattr(self, method)('reports', api_key=self.api_key, *vargs, **kwargs)

    def get_watches(self, *vargs, **kwargs):
        return self._request_watches('get', *vargs, **kwargs)

    def create_watch(self, data, *vargs, **kwargs):
        return self._request_watches('put', data=data, *vargs, **kwargs)

    def delete_watch(self, data, *vargs, **kwargs):
        return self._request_watches('delete', data=data, *vargs, **kwargs)

    def run_jobs(self):
        self.get('trigger_reports', api_key=self.api_key)
