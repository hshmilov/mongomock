import pytest
from services.adapters.hyper_v_service import HyperVService, hyper_v_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_hyper_v_credentials import *

# Hyper-V is part of our sanity tests since it uses the wmi runner to fetch devices from hyperv. Since this
# is a big part of the execution it could affect hyper-v (it indeed affects hyper-v a lot)


class TestHyperVAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return HyperVService()

    @property
    def some_client_id(self):
        return client_details['host']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass

    @pytest.mark.skip("Skipping due to setting up vhd")
    def test_fetch_devices(self):
        pass
