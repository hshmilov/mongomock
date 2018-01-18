import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class QualysScansService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__(service_dir='../adapters/qualys-scans-adapter', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def qualys_scans_fixture(request):
    service = QualysScansService()
    initialize_fixture(request, service)
    return service
