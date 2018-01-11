import pytest
from services.axonius_service import get_service


@pytest.fixture(scope="session", autouse=True)
def axonius_fixture(request):
    system = get_service()

    for service in system.axonius_services:
        # we start the process so we own it
        service.take_process_ownership()

        # good cleanup before the test run
        service.stop(should_delete=True)

        # spawn docker in parallel for all
        service.start()

    for service in system.axonius_services:
        service.wait_for_service()
        request.addfinalizer(lambda: service.stop(should_delete=True))

    return system
