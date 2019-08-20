import re

import pytest
from flaky import flaky

from axonius.consts.metric_consts import Adapters
from axonius.utils.wait import wait_until
from services.adapters.esx_service import EsxService, esx_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_bad_credentials import FAKE_CLIENT_DETAILS
from test_credentials.test_esx_credentials import *


class TestEsxAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return EsxService()

    @property
    def some_client_id(self):
        # Not importing the adapter itself because ESX has some weird dependencies
        return '{}/{}'.format(self.some_client_details['host'], self.some_client_details['user'])

    @property
    def some_client_details(self):
        return dict(client_details[0][0])

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('Not working')
    def test_fetch_devices(self):
        client_details_to_send = []
        for client, some_device_id in client_details:
            client = dict(client)
            self.adapter_service.add_client(client)
            client_id = '{}/{}'.format(client['host'], client['user'])
            client_details_to_send.append((client_id, some_device_id))
        self.axonius_system.assert_device_aggregated(self.adapter_service, client_details_to_send)
        assert not self.axonius_system.get_device_by_id(self.adapter_service.unique_name, VERIFY_DEVICE_MISSING)
        tagged_device = self.axonius_system.get_device_by_id(self.adapter_service.unique_name, DEVICE_WITH_TAG)
        assert tagged_device, 'tagged device not present'
        tags = tagged_device[0]['adapters'][0]['data']['tags']
        assert len(tags) == 1
        assert tags[0]['tag_key'] == TAG_KEY
        assert tags[0]['tag_value'] == TAG_VALUE

    @flaky(max_runs=3)
    def test_folder_on_dc_level(self):
        self.drop_clients()

        client, _ = client_details[0]
        client = dict(client)

        client_id = '{}/{}'.format(client['host'], client['user'])
        self.adapter_service.add_client(client)

        self.axonius_system.assert_device_aggregated(self.adapter_service, [(client_id, AGGREGATED_DEVICE_ID)])

    @pytest.mark.skip('Not working')
    def test_check_reachability(self):
        assert self.adapter_service.is_client_reachable(self.some_client_details)
        assert not self.adapter_service.is_client_reachable(FAKE_CLIENT_DETAILS)

    def test_bad_client(self):
        # testing specifically for valid but unreachable client
        bad_client = dict(client_details[0][0])
        bad_client['host'] = 'totally_not_an_esx_host'

        self.adapter_service.add_client(bad_client)

        # make sure we passed the parse creds
        wait_until(lambda: self.log_tester.is_pattern_in_log(re.escape('Unable to access vCenter'), 10))
        # make sure log is written
        wait_until(
            lambda: self.log_tester.is_metric_in_log(metric_name=Adapters.CREDENTIALS_CHANGE_ERROR,
                                                     value='.*',
                                                     lines_lookback=10))
