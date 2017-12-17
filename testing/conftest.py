import pytest

from services.axonius_service import get_service
from services.simple_fixture import initialize_fixture


@pytest.fixture(scope="session", autouse=True)
def axonius_fixture(request):
    service = get_service(should_start=True)

    initialize_fixture(request, service.db)
    initialize_fixture(request, service.core)
    initialize_fixture(request, service.aggregator)

    return service
