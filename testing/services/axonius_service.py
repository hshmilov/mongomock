import time
from datetime import datetime, timedelta

from test_helpers.utils import try_until_not_thrown
from services.aggregator_service import AggregatorService
from services.core_service import CoreService
from services.mongo_service import MongoService

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


def get_service():
    mongo = MongoService()
    core = CoreService()
    aggregator = AggregatorService()
    return AxoniusService(mongo, core, aggregator)


class AxoniusService(object):
    def __init__(self, db, core, aggregator):
        self.db = db
        self.core = core
        self.aggregator = aggregator

    def stop(self, should_delete):
        self.aggregator.stop(should_delete)
        self.core.stop(should_delete)
        self.db.stop(should_delete)

    def start_and_wait(self):
        # Start in parallel
        self.db.start()
        self.core.start()
        self.aggregator.start()

        # wait for all
        self.db.wait_for_service()
        self.core.wait_for_service()
        self.aggregator.wait_for_service()

    def get_devices_with_condition(self, cond):
        cursor = self.db.client[self.aggregator.unique_name]['devices_db'].find(cond)
        return list(cursor)

    def get_device_by_id(self, adapter_name, device_id):
        cond = {'adapters.data.id': device_id, 'adapters.plugin_unique_name': adapter_name}
        return self.get_devices_with_condition(cond)

    def clear_all_devices(self):
        aggregator_unique_name = self.aggregator.unique_name
        self.aggregator.stop(should_delete=False)
        self.db.client.drop_database(aggregator_unique_name)
        self.aggregator.start_and_wait()

    def get_device_network_interfaces(self, adapter_name, device_id):
        device = self.get_device_by_id(adapter_name, device_id)
        adapter_device = next(adapter_device for adapter_device in device[0]['adapters'] if
                              adapter_device[PLUGIN_UNIQUE_NAME] == adapter_name)
        return adapter_device['data']['network_interfaces']

    def assert_device_aggregated(self, adapter, client_id, some_device_id, max_tries=30):
        self.aggregator.query_devices(adapter_id=adapter.unique_name)  # send trigger to agg to refresh devices
        devices_as_dict = adapter.devices()
        assert client_id in devices_as_dict

        # check the device is read by adapter
        devices_list = devices_as_dict[client_id]['parsed']
        assert len(list(filter(lambda device: device['id'] == some_device_id, devices_list))) == 1

        # check that the device is collected by aggregator and now in db

        def assert_device_inserted():
            devices = self.get_device_by_id(adapter.unique_name, some_device_id)
            assert len(devices) == 1

        try_until_not_thrown(max_tries, 10, assert_device_inserted)

    def restart_plugin(self, plugin):
        """
        :param plugin: plugint to restart
        note: restarting plugin does not delete its volume
        """
        plugin.stop(should_delete=False)
        plugin.start()
        plugin.wait_for_service()
        assert plugin.is_plugin_registered(self.core)

    def restart_core(self):
        self.core.stop()
        # Check that Aggregator really went down
        current_time = datetime.now()
        self.aggregator.trigger_check_registered()
        while self.aggregator.is_up():
            assert datetime.now() - current_time < timedelta(seconds=10)
            time.sleep(1)
        # Now aggregator is down as well
        self.core.start_and_wait()

        def assert_aggregator_registered():
            assert self.aggregator.is_up()
            assert self.aggregator.is_plugin_registered(self.core)

        try_until_not_thrown(30, 1, assert_aggregator_registered)
