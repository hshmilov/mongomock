import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BitFitService(AdapterService):
    def __init__(self):
        super().__init__('bit-fit')


@pytest.fixture(scope='module', autouse=True)
def bit_fit_fixture(request):
    service = BitFitService()
    initialize_fixture(request, service)
    return service
