# we need fixture so ignore unused
# pylint: disable=W0611
import pytest

from services.adapters.sophos_service import SophosService, sophos_fixture
from test_credentials.test_sophos_credentials import (SOME_DEVICE_ID,
                                                      client_details)
from test_helpers.adapter_test_base import AdapterTestBase


class TestSophosAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SophosService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_user_id(self):
        raise NotImplementedError

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('Failing PR #1965')
    def test_fetch_devices(self):
        super().test_fetch_devices()
