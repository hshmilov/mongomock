import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ProofpointService(AdapterService):
    def __init__(self):
        super().__init__('proofpoint')


@pytest.fixture(scope='module', autouse=True)
def proofpoint_fixture(request):
    service = ProofpointService()
    initialize_fixture(request, service)
    return service
