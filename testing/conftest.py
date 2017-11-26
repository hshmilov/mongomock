import pytest

from services.mongo_service import MongoService
from services.core_service import CoreService
from services.aggregator_service import AggregatorService
from services.simple_fixture import initalize_fixture
from test_helpers.utils import try_until_not_thrown


class AxoniusService(object):
    def __init__(self, db, core, aggregator):
        self.db = db
        self.core = core
        self.aggregator = aggregator

    def get_devices_with_condition(self, cond):
        cursor = self.db.client[self.aggregator.unique_name]['devices_db'].find(
            cond)
        return list(cursor)

    def get_device_by_id(self, adapter_name, device_id):
        cond = {'adapters.{0}.data.id'.format(adapter_name): device_id}
        return self.get_devices_with_condition(cond)

    def add_client_to_adapter(self, adapter, client_details, client_id):
        adapter.add_client(self.db, client_details, client_id)
        self.aggregator.query_devices()  # send trigger to agg to refresh devices

    def assert_device_aggregated(self, adapter, client_id, some_device_id):
        devices_as_dict = adapter.devices()
        assert client_id in devices_as_dict

        # check the device is read by adapter
        devices_list = devices_as_dict[client_id]['parsed']
        assert 1 == len(
            list(filter(lambda device: device['id'] == some_device_id, devices_list)))

        # check that the device is collected by aggregator and now in db

        def assert_device_inserted():
            devices = self.get_device_by_id(
                adapter.unique_name, some_device_id)
            assert len(devices) == 1

        try_until_not_thrown(50, 0.20, assert_device_inserted)

    def restart_plugin(self, plugin):
        plugin.stop()
        plugin.start()
        plugin.wait_for_service()
        assert plugin.is_plugin_registered(self.core)


@pytest.fixture(scope="session", autouse=True)
def axonius_fixture(request):
    mongo = MongoService()
    initalize_fixture(request, mongo)

    core = CoreService()
    initalize_fixture(request, core)

    aggregator = AggregatorService()
    initalize_fixture(request, aggregator)

    return AxoniusService(mongo, core, aggregator)
