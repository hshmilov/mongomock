import pytest
import bcrypt

from services.axonius_service import get_service
import testing.test_credentials.test_gui_credentials


def axonius_set_test_passwords():
    axonius_system = get_service()
    gui_creds = testing.test_credentials.test_gui_credentials
    users = [gui_creds.AXONIUS_USER, gui_creds.AXONIUS_RO_USER, gui_creds.DEFAULT_USER]
    for u in users:
        _set_password(axonius_system, u['user_name'], u['password'])


def _set_password(axonius_system, username, password):
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    axonius_system.db.gui_users_collection().update_one(
        {'user_name':  username},
        {'$set': {'password': hashed_password}}
    )


@pytest.fixture(scope='session', autouse=True)
def axonius_fixture(request):
    axonius_system = get_service()

    axonius_system.take_process_ownership()  # we start the process so we own it

    axonius_system.stop(should_delete=True)  # good cleanup before the test run

    axonius_system.start_and_wait()  # spawn docker in parallel for all

    axonius_set_test_passwords()

    request.addfinalizer(lambda: axonius_system.stop(should_delete=True))

    return axonius_system
