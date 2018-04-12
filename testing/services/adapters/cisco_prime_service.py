import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CiscoPrimeService(AdapterService):
    def __init__(self):
        super().__init__('cisco-prime')


@pytest.fixture(scope="module", autouse=True)
def cisco_prime_fixture(request):
    service = CiscoPrimeService()
    initialize_fixture(request, service)
    return service
