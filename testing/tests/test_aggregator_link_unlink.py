import pytest

# pylint: disable=redefined-outer-name,unused-import
from services.adapters.ad_service import ad_fixture
from services.adapters.esx_service import esx_fixture


def test_aggregator_is_up(axonius_fixture):
    assert axonius_fixture.aggregator.is_up()


def test_registered(axonius_fixture):
    assert axonius_fixture.aggregator.is_plugin_registered(axonius_fixture.core)


@pytest.mark.skip('AX-1977')
def test_minimum_fetch_wait_time(axonius_fixture, esx_fixture):
    def _get_update_time(adapter_name, device_id=None):
        # Getting device from esx
        if device_id:
            devices_response = axonius_fixture.get_devices_with_condition({'adapters.data.id': device_id})
        else:
            devices_response = axonius_fixture.get_devices_with_condition({})
        first_esx_device = next((d for d in devices_response if d['adapters'][0]['plugin_name'] == 'esx_adapter'), None)
        assert first_esx_device is not None, 'No ESX device found'
        for adapter_data in first_esx_device['adapters']:
            if adapter_data['plugin_name'] == adapter_name:
                return adapter_data['data']['id'], adapter_data['accurate_for_datetime']
        return None

    scheduler = axonius_fixture.scheduler
    # Getting the update time before fetching
    device_id, device_update_time_old = _get_update_time('esx_adapter')
    # Sanity check that the device can be fatched
    esx_fixture.set_configurable_config('AdapterBase', 'minimum_time_until_next_fetch')  # Will delete this option
    scheduler.start_research()
    scheduler.wait_for_scheduler(False)
    scheduler.wait_for_scheduler(True)
    _, device_update_time_new = _get_update_time('esx_adapter', device_id)
    assert device_update_time_old < device_update_time_new, f'Device {device_id} didnt fetched on the second try'
    device_update_time_old = device_update_time_new
    # Now changing the minimum and try again (should not get updated)
    esx_fixture.set_configurable_config('AdapterBase', 'minimum_time_until_next_fetch', 20)

    scheduler.start_research()
    scheduler.wait_for_scheduler(False)
    scheduler.wait_for_scheduler(True)
    _, device_update_time_new = _get_update_time('esx_adapter', device_id)
    assert device_update_time_new == device_update_time_old, f'Device {device_id} fetched although it shouldnt. ' \
                                                             f'old time - {device_update_time_old}, ' \
                                                             f'new time - {device_update_time_new}'
    esx_fixture.set_configurable_config('AdapterBase', 'minimum_time_until_next_fetch')
