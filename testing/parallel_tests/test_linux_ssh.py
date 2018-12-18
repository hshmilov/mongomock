# pylint: disable=unused-import
from services.adapters.linux_ssh_service import LinuxSshService, linux_ssh_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_linux_ssh_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from linux_ssh_adapter.client_id import get_client_id


class TestLinuxSshAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return LinuxSshService()

    @property
    def adapter_name(self):
        return 'linux_ssh_adapter'

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError()
