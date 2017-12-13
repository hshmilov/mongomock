from services.ad_service import ad_fixture
from services.esx_service import esx_fixture
from test_helpers import utils

import pytest


def test_aggregator_is_up(axonius_fixture):
    assert axonius_fixture.aggregator.is_up()


def test_registered(axonius_fixture):
    assert axonius_fixture.aggregator.is_plugin_registered(axonius_fixture.core)


def test_fetch_complicated_link(axonius_fixture, ad_fixture, esx_fixture):
    axonius_fixture.clear_all_devices()

    utils.populate_test_devices(axonius_fixture, ad_fixture)
    utils.populate_test_devices_esx(axonius_fixture, esx_fixture)

    devices_response = axonius_fixture.get_devices_with_condition({})

    first_ad_device = next((d for d in devices_response if d['adapters'][0]['plugin_name'] == 'ad_adapter'), None)
    assert first_ad_device is not None, "No AD device found"

    first_esx_device = next((d for d in devices_response if d['adapters'][0]['plugin_name'] == 'esx_adapter'), None)
    assert first_esx_device is not None, "No ESX device found"

    axonius_fixture.aggregator.add_tag("ad_taggy", first_ad_device['adapters'][0]['plugin_unique_name'],
                                       first_ad_device['adapters'][0]['data']['id'])
    assert any(
        x['tags'] and x['tags'][0]['tagname'] == 'ad_taggy' and
        x['adapters'][0]['plugin_unique_name'] == first_ad_device['adapters'][0]['plugin_unique_name'] and
        x['adapters'][0]['data']['id'] == first_ad_device['adapters'][0]['data']['id']
        for x in axonius_fixture.get_devices_with_condition({})), "Tagging AD failed"

    axonius_fixture.aggregator.add_tag("esx_taggy", first_esx_device['adapters'][0]['plugin_unique_name'],
                                       first_esx_device['adapters'][0]['data']['id'])

    assert any(
        x['tags'] and x['tags'][0]['tagname'] == 'esx_taggy' and
        x['adapters'][0]['plugin_unique_name'] == first_esx_device['adapters'][0]['plugin_unique_name'] and
        x['adapters'][0]['data']['id'] == first_esx_device['adapters'][0]['data']['id']
        for x in axonius_fixture.get_devices_with_condition({})), "Tagging esx failed"

    axonius_fixture.aggregator.link({
        first_ad_device['adapters'][0]['plugin_unique_name']: first_ad_device['adapters'][0]['data']['id'],
        first_esx_device['adapters'][0]['plugin_unique_name']: first_esx_device['adapters'][0]['data']['id'],
    })

    devices_response = axonius_fixture.get_devices_with_condition({})
    assert not any(
        len(x['adapters']) == 1 and
        (x['adapters'][0]['plugin_unique_name'] == first_ad_device['adapters'][0]['plugin_unique_name'] and
         x['adapters'][0]['data']['id'] == first_ad_device['adapters'][0]['data']['id']) or
        (x['adapters'][0]['plugin_unique_name'] == first_esx_device['adapters'][0]['plugin_unique_name'] and
         x['adapters'][0]['data']['id'] == first_esx_device['adapters'][0]['data']['id'])
        for x in devices_response), "Link didn't remove instance or 'old' device"

    linked_device = next((x for x in devices_response
                          if len(x['adapters']) == 2 and
                          any(y['plugin_unique_name'] == first_ad_device['adapters'][0]['plugin_unique_name'] and
                              y['data']['id'] == first_ad_device['adapters'][0]['data']['id'] for y in
                              x['adapters'])
                          and
                          any(y['plugin_unique_name'] == first_esx_device['adapters'][0][
                              'plugin_unique_name'] and
                              y['data']['id'] == first_esx_device['adapters'][0]['data']['id'] for y in
                              x['adapters'])

                          ), None)
    assert linked_device is not None, "Can't find instance of linked device"

    assert any(x['tagname'] == 'esx_taggy' for x in linked_device['tags']), "ESX tag is gone"
    assert any(x['tagname'] == 'ad_taggy' for x in linked_device['tags']), "AD tag is gone"

    axonius_fixture.clear_all_devices()
