# we need fixture so ignore unused
# pylint: disable=W0611
import pytest
from services.adapters.datadog_service import (DatadogService, datadog_fixture)
from test_credentials.test_datadog_credentials import (SOME_DEVICE_ID,
                                                       client_details,
                                                       OLD_CLIENT_DETAILS)
from test_helpers.adapter_test_base import AdapterTestBase


class TestDatadogAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return DatadogService()

    @property
    def some_client_id(self):
        return OLD_CLIENT_DETAILS['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_user_id(self):
        raise NotImplementedError

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('No test environment.')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('No creds')
    def test_check_reachability(self):
        pass
