from multiprocessing import cpu_count
import pytest
from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture


class HeavyLiftingService(PluginService):
    def __init__(self):
        super().__init__('heavy-lifting')

    @property
    def get_max_uwsgi_threads(self) -> int:
        # A couple of threads so this will keep answering core
        return 3

    @property
    def get_uwsgi_max_listen_conns(self) -> int:
        return 10000

    @property
    def get_max_uwsgi_processes(self) -> int:
        return (cpu_count() - 1) or 1

    @property
    def get_min_uwsgi_processes(self) -> int:
        return 0


@pytest.fixture(scope='module')
def heavy_lifting_fixture(request):
    service = HeavyLiftingService()
    initialize_fixture(request, service)
    return service
