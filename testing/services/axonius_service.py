import time
from datetime import datetime, timedelta

from axonius.device import NETWORK_INTERFACES_FIELD
from test_helpers.utils import try_until_not_thrown
from services.aggregator_service import AggregatorService
from services.core_service import CoreService
from services.mongo_service import MongoService
from services.gui_service import GuiService

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


def get_service():
    mongo = MongoService()
    core = CoreService()
    aggregator = AggregatorService()
    gui = GuiService()
    return AxoniusService(mongo, core, aggregator, gui)


class AxoniusService(object):
    def __init__(self, db, core, aggregator, gui):
        self.db = db
        self.core = core
        self.aggregator = aggregator
        self.gui = gui

        self.axonius_services = [db, core, aggregator, gui]

    def stop(self, should_delete):
        # Not critical but lets stop in reverse order
        for service in self.axonius_services[::-1]:
            service.stop(should_delete)

    def start_and_wait(self):
        # Start in parallel
        for service in self.axonius_services:
            service.start()

        # wait for all
        for service in self.axonius_services:
            service.wait_for_service()

    def get_devices_db(self):
        return self.db.get_devices_db(self.aggregator.unique_name)

    def insert_device(self, device_data):
        self.get_devices_db().insert_one(device_data)

    def get_devices_with_condition(self, cond):
        cursor = self.get_devices_db().find(cond)
        return list(cursor)

    def get_device_by_id(self, adapter_name, device_id):
        cond = {'adapters.data.id': device_id, 'adapters.plugin_unique_name': adapter_name}
        return self.get_devices_with_condition(cond)

    def get_device_network_interfaces(self, adapter_name, device_id):
        device = self.get_device_by_id(adapter_name, device_id)
        adapter_device = next(adapter_device for adapter_device in device[0]['adapters'] if
                              adapter_device[PLUGIN_UNIQUE_NAME] == adapter_name)
        return adapter_device['data'][NETWORK_INTERFACES_FIELD]

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
        plugin.start_and_wait()
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
