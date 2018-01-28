import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class QualysService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__('qualys', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def qualys_fixture(request):
    service = QualysService()
    initialize_fixture(request, service)
    return service
