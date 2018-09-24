# we need fixture so ignore unused
# pylint: disable=W0611
import pytest

from services.adapters.deep_security_service import (DeepSecurityService,
                                                     deep_security_fixture)
from test_credentials.test_deep_security_credentials import (SOME_DEVICE_ID,
                                                             client_details)
from test_helpers.adapter_test_base import AdapterTestBase


class TestDeepSecurityAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return DeepSecurityService()

    @property
    def some_client_id(self):
        return (client_details.get('domain') or '') + (client_details.get('tenant') or '') + client_details['username']

    @property
    def some_user_id(self):
        raise NotImplementedError

    @pytest.mark.skip('Not Implemented')
    def test_check_reachability(self):
        pass

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
