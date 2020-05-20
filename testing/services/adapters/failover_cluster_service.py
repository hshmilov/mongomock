import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class FailoverClusterService(AdapterService):
    def __init__(self):
        super().__init__('failover-cluster')


@pytest.fixture(scope='module', autouse=True)
def failover_cluster_fixture(request):
    service = FailoverClusterService()
    initialize_fixture(request, service)
    return service
