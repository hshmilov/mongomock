# redefined-outer-name is needed since we are defining imported fixtures as var names (ad_fixture, for instance).
# This is a common procedure with pylint and is disabled by default.
# pylint: disable=unused-import, too-many-statements, too-many-locals, redefined-outer-name, too-many-branches
import logging

from tests.conftest import axonius_fixture
from services.adapters.ad_service import ad_fixture
from services.axonius_service import get_service
from services.plugins.device_control_service import device_control_fixture
from services.plugins.general_info_service import general_info_fixture
from test_credentials.test_ad_credentials import ad_client1_details
from testing.test_credentials.test_gui_credentials import DEFAULT_USER
from examples.api_usage import RESTExample


def test_api(axonius_fixture, general_info_fixture, device_control_fixture, ad_fixture):
    axonius_system = get_service()

    ad_fixture.add_client(ad_client1_details)

    axonius_system.scheduler.start_research()
    axonius_system.scheduler.wait_for_scheduler(True)

    axonius_system.core.set_config(
        {
            'config.execution_settings.enabled': True,
            'config.execution_settings.pm_rpc_enabled': True,
            'config.execution_settings.pm_smb_enabled': True,
        }
    )

    client = RESTExample('https://127.0.0.1',
                         auth=(DEFAULT_USER['user_name'], DEFAULT_USER['password']),
                         verify=False)
    for name in client.get_examples():
        logging.info(f'Calling api function "{name}"')
        callback = getattr(client, name)
        callback()
        logging.info('\n\n')
