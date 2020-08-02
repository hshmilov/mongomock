# we need fixture so ignore unused
# pylint: disable=W0611
from services.adapters.crowd_strike_service import (CrowdStrikeService,
                                                    crowd_strike_fixture)
from test_credentials.test_crowd_strike_credentials import (SOME_DEVICE_ID,
                                                            client_details)
from test_helpers.adapter_test_base import AdapterTestBase


class TestCrowdStrikeAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CrowdStrikeService()

    @property
    def some_client_id(self):
        return client_details['domain'] + '_' + client_details['username']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_user_id(self):
        raise NotImplementedError

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
