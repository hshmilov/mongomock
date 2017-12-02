import pytest
from test_helpers import utils


def test_restart_data_persistency(axonius_fixture):
    initial_devices = list(
        axonius_fixture.db.get_collection(axonius_fixture.aggregator.unique_name, 'devices_db').find())
    if len(initial_devices) < 3:
        utils.populate_test_devices(axonius_fixture)
        initial_devices = list(axonius_fixture.db.get_collection(
            axonius_fixture.aggregator.unique_name, 'devices_db').find())

    axonius_fixture.db.stop()
    axonius_fixture.db.start_and_wait()

    after_restart_devices = list(axonius_fixture.db.get_collection(
        axonius_fixture.aggregator.unique_name, 'devices_db').find())

    assert after_restart_devices == initial_devices
