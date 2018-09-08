import pytest
from flaky import flaky
from retrying import retry

# pylint: disable=redefined-outer-name,unused-import
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.consts.scheduler_consts import Phases, StateLevels
from services.adapters.ad_service import ad_fixture
from services.adapters.esx_service import esx_fixture
from test_credentials import test_esx_credentials
from test_helpers import utils

pytestmark = pytest.mark.sanity


def test_aggregator_is_up(axonius_fixture):
    assert axonius_fixture.aggregator.is_up()


def test_registered(axonius_fixture):
    assert axonius_fixture.aggregator.is_plugin_registered(axonius_fixture.core)


@flaky(max_runs=2)
def test_fetch_complicated_link(axonius_fixture, ad_fixture, esx_fixture):
    utils.populate_test_devices(axonius_fixture, ad_fixture)
    utils.populate_test_devices_esx(axonius_fixture, esx_fixture)

    devices_response = axonius_fixture.get_devices_with_condition({})

    first_ad_device = next((d for d in devices_response
                            if d['adapters'][0]['plugin_name'] == 'active_directory_adapter'), None)
    assert first_ad_device is not None, 'No AD device found'

    first_esx_device = next((d for d in devices_response if d['adapters'][0]['plugin_name'] == 'esx_adapter'), None)
    assert first_esx_device is not None, 'No ESX device found'

    axonius_fixture.aggregator.add_label('ad_taggy', first_ad_device['adapters'][0][PLUGIN_UNIQUE_NAME],
                                         first_ad_device['adapters'][0]['data']['id'], 'devices')
    assert any(
        x['tags'] and x['tags'][0]['name'] == 'ad_taggy' and
        x['adapters'][0][PLUGIN_UNIQUE_NAME] == first_ad_device['adapters'][0][PLUGIN_UNIQUE_NAME] and
        x['adapters'][0]['data']['id'] == first_ad_device['adapters'][0]['data']['id']
        for x in axonius_fixture.get_devices_with_condition({})), 'Tagging AD failed'

    axonius_fixture.aggregator.add_label('esx_taggy', first_esx_device['adapters'][0][PLUGIN_UNIQUE_NAME],
                                         first_esx_device['adapters'][0]['data']['id'], 'devices')

    assert any(
        x['tags'] and x['tags'][0]['name'] == 'esx_taggy' and
        x['adapters'][0][PLUGIN_UNIQUE_NAME] == first_esx_device['adapters'][0][PLUGIN_UNIQUE_NAME] and
        x['adapters'][0]['data']['id'] == first_esx_device['adapters'][0]['data']['id']
        for x in axonius_fixture.get_devices_with_condition({})), 'Tagging esx failed'

    axonius_fixture.aggregator.link([
        (first_ad_device['adapters'][0][PLUGIN_UNIQUE_NAME], first_ad_device['adapters'][0]['data']['id']),
        (first_esx_device['adapters'][0][PLUGIN_UNIQUE_NAME], first_esx_device['adapters'][0]['data']['id']),
    ], 'devices')

    devices_response = axonius_fixture.get_devices_with_condition({})
    assert not any(
        len(x['adapters']) == 1 and
        (x['adapters'][0][PLUGIN_UNIQUE_NAME] == first_ad_device['adapters'][0][PLUGIN_UNIQUE_NAME] and
         x['adapters'][0]['data']['id'] == first_ad_device['adapters'][0]['data']['id']) or
        (x['adapters'][0][PLUGIN_UNIQUE_NAME] == first_esx_device['adapters'][0][PLUGIN_UNIQUE_NAME] and
         x['adapters'][0]['data']['id'] == first_esx_device['adapters'][0]['data']['id'])
        for x in devices_response), 'Link didn\'t remove instance or \'old\' device'

    linked_device = next((x for x in devices_response
                          if len(x['adapters']) == 2 and
                          any(y[PLUGIN_UNIQUE_NAME] == first_ad_device['adapters'][0][PLUGIN_UNIQUE_NAME] and
                              y['data']['id'] == first_ad_device['adapters'][0]['data']['id'] for y in
                              x['adapters'])
                          and
                          any(y[PLUGIN_UNIQUE_NAME] == first_esx_device['adapters'][0][
                              PLUGIN_UNIQUE_NAME] and
                              y['data']['id'] == first_esx_device['adapters'][0]['data']['id'] for y in
                              x['adapters'])

                          ), None)
    assert linked_device is not None, 'Can\'t find instance of linked device'

    assert any(x['name'] == 'esx_taggy' for x in linked_device['tags']), 'ESX tag is gone'
    assert any(x['name'] == 'ad_taggy' for x in linked_device['tags']), 'AD tag is gone'
    axonius_fixture.aggregator.unlink([
        (first_ad_device['adapters'][0][PLUGIN_UNIQUE_NAME], first_ad_device['adapters'][0]['data']['id'])
    ], 'devices')
    devices_response = axonius_fixture.get_devices_with_condition({})
    assert not any(
        len(x['adapters']) == 2
        for x in devices_response), 'Unlink didn\'t remove linked instance or \'old\' device'

    assert any(
        (x['adapters'][0][PLUGIN_UNIQUE_NAME] == first_ad_device['adapters'][0][PLUGIN_UNIQUE_NAME] and
         x['adapters'][0]['data']['id'] == first_ad_device['adapters'][0]['data']['id']) for x in devices_response)
    assert any(
        (x['adapters'][0][PLUGIN_UNIQUE_NAME] == first_esx_device['adapters'][0][PLUGIN_UNIQUE_NAME] and
         x['adapters'][0]['data']['id'] == first_esx_device['adapters'][0]['data']['id']) for x in devices_response)

    assert any(
        (x['adapters'][0][PLUGIN_UNIQUE_NAME] == first_ad_device['adapters'][0][PLUGIN_UNIQUE_NAME] and
         x['adapters'][0]['data']['id'] == first_ad_device['adapters'][0]['data']['id'] and
         x['tags'][0]['name'] == 'ad_taggy') for x in devices_response)
    assert any(
        (x['adapters'][0][PLUGIN_UNIQUE_NAME] == first_esx_device['adapters'][0][PLUGIN_UNIQUE_NAME] and
         x['adapters'][0]['data']['id'] == first_esx_device['adapters'][0]['data']['id'] and
         x['tags'][0]['name'] == 'esx_taggy') for x in devices_response)


def test_minimum_fetch_wait_time(axonius_fixture, esx_fixture):
    @retry(stop_max_attempt_number=100, wait_fixed=1000, retry_on_result=lambda result: result is False)
    def _wait_for_state(scheduler_instance, cond):
        state = scheduler_instance.current_state().json()
        return (state[StateLevels.Phase.name] == Phases.Stable.name) == cond

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
    _wait_for_state(scheduler, False)
    _wait_for_state(scheduler, True)
    _, device_update_time_new = _get_update_time('esx_adapter', device_id)
    assert device_update_time_old < device_update_time_new, f'Device {device_id} didnt fetched on the second try'
    device_update_time_old = device_update_time_new
    # Now changing the minimum and try again (should not get updated)
    esx_fixture.set_configurable_config('AdapterBase', 'minimum_time_until_next_fetch', 20)

    scheduler.start_research()
    _wait_for_state(scheduler, False)
    _wait_for_state(scheduler, True)
    _, device_update_time_new = _get_update_time('esx_adapter', device_id)
    assert device_update_time_new == device_update_time_old, f'Device {device_id} fetched although it shouldnt. ' \
                                                             f'old time - {device_update_time_old}, ' \
                                                             f'new time - {device_update_time_new}'
    esx_fixture.set_configurable_config('AdapterBase', 'minimum_time_until_next_fetch')
