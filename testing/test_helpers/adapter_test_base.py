import pytest
from services.axonius_service import get_service
from test_helpers.utils import check_conf


class AdapterTestBase(object):
    """
    Basic tests for adapter are defined here.
    If one wants to skip or modify a test he can do that by overriding the corresponding method.
    If one wants to skip a test - he can do that by overriding and marking the test with @pytest.mark.skip
    """
    axonius_service = get_service()

    @property
    def adapter_service(self):
        raise NotImplementedError

    @property
    def adapter_name(self):
        raise NotImplementedError

    @property
    def some_client_id(self):
        raise NotImplementedError

    @property
    def some_client_details(self):
        raise NotImplementedError

    @property
    def some_device_id(self):
        raise NotImplementedError

    def drop_clients(self):
        self.axonius_service.db.client[self.adapter_service.unique_name].drop_collection('clients')

    def test_adapter_is_up(self):
        assert self.adapter_service.is_up()

    def test_adapter_responds_to_schema(self):
        assert self.adapter_service.schema().status_code == 200

    def test_adapter_in_configs(self):
        check_conf(self.axonius_service, self.adapter_service, self.adapter_name)

    def test_check_registration(self):
        assert self.adapter_service.is_plugin_registered(self.axonius_service.core)

    def test_fetch_devices(self):
        self.adapter_service.add_client(self.some_client_details)
        self.axonius_service.assert_device_aggregated(self.adapter_service, self.some_client_id, self.some_device_id)

    def test_restart(self):
        service = self.adapter_service
        # it's ok to restart adapter in adapter test
        service.take_process_ownership()
        self.axonius_service.restart_plugin(service)
