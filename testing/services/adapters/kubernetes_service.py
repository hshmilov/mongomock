import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class KubernetesService(AdapterService):
    def __init__(self):
        super().__init__('kubernetes')


@pytest.fixture(scope='module', autouse=True)
def kubernetes_fixture(request):
    service = KubernetesService()
    initialize_fixture(request, service)
    return service
