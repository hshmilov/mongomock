import pytest

from services.axonius_service import get_service
from testing.test_credentials.test_gui_credentials import axonius_set_test_passwords


@pytest.fixture(scope='session', autouse=True)
def axonius_fixture(request):
    axonius_system = get_service()

    axonius_system.take_process_ownership()  # we start the process so we own it

    axonius_system.stop(should_delete=True)  # good cleanup before the test run

    axonius_system.start_and_wait()  # spawn docker in parallel for all

    axonius_set_test_passwords()

    request.addfinalizer(lambda: axonius_system.stop(should_delete=True))

    return axonius_system
