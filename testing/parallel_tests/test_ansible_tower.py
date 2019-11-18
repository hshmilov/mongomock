# pylint: disable=unused-import
# pylint: disable=E0401
import requests
import pytest
from axonius.utils.json import from_json
from services.adapters.ansible_tower_service import AnsibleTowerService, ansible_tower_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_ansible_tower_credentials import CLIENT_DETAILS
from ansible_tower_adapter.client_id import get_client_id


ADAPTER_NAME = 'ansible_tower_adapter'


class TestAnsibleTowerAdapter(AdapterTestBase):

    @classmethod
    def get_ans_host(cls):
        host_uri = CLIENT_DETAILS['domain'] + '/api/v2/hosts/100'
        auth = (CLIENT_DETAILS['username'], CLIENT_DETAILS['password'])
        response = requests.get(host_uri, auth=auth)
        if response.status_code == 200:
            return from_json(response.content)
        return None

    @property
    def adapter_service(self):
        return AnsibleTowerService()

    @property
    def adapter_name(self):
        return ADAPTER_NAME

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        ans_host = self.get_ans_host()
        return str(ans_host.get('id')) + '_' + ans_host.get('name')

    @property
    def some_user_id(self):
        raise NotImplementedError()

    def test_fetch_devices(self):
        super().test_fetch_devices()
        axon_hosts = self.adapter_service.devices()
        axon_hosts = axon_hosts.get(self.some_client_id).get('parsed')
        axon_total = len(axon_hosts)
        host_uri = CLIENT_DETAILS['domain'] + '/api/v2/hosts'
        auth = (CLIENT_DETAILS['username'], CLIENT_DETAILS['password'])
        response = requests.get(host_uri, auth=auth)
        if response.status_code == 200:
            ans_hosts = from_json(response.content)

        awx_total = ans_hosts['count'] - 1
        assert axon_total == awx_total

        awx_host = self.get_ans_host()
        awx_host_id = str(awx_host.get('id')) + '_' + awx_host.get('name')

        for host in axon_hosts:
            if host.get('id') == awx_host_id:
                axon_host = host
                break

        if axon_host.get('cloud_id'):
            axon_cloud_id = axon_host.get('cloud_id')
            awx_data_variables = from_json(awx_host.get('variables'))
            if 'ec2_id' in awx_data_variables:
                assert axon_cloud_id == awx_data_variables.get('ec2_id')
                assert axon_host.get('cloud_provider') == 'AWS'
            elif 'gce_id' in awx_data_variables:
                assert axon_cloud_id == awx_data_variables.get('gce_id')
                assert axon_host.get('cloud_provider') == 'GCP'
            elif 'deviceId' in awx_data_variables:
                assert axon_cloud_id == awx_data_variables.get('deviceId')
                assert axon_host.get('cloud_provider') == 'azure'
            else:
                pytest.skip('skipping unknown cloud_id format type, is it a new cloud provider ? ')
