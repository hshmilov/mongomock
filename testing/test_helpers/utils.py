import time

from axonius.consts.adapter_consts import DEVICE_SAMPLE_RATE


def try_until_not_thrown(times, sleep_period, runnable, *args, **kwargs):
    success = False
    for x in range(1, times):
        try:
            runnable(*args, **kwargs)
            success = True
            return
        except:
            time.sleep(sleep_period)
    assert success


def populate_test_devices(axonius_fixture, ad_fixture):
    from parallel_tests.test_ad import ad_client1_details, DEVICE_ID_FOR_CLIENT_1

    client_id = ad_client1_details['dc_name']
    assert ad_fixture.is_up()

    ad_fixture.add_client(ad_client1_details)
    axonius_fixture.assert_device_aggregated(ad_fixture, client_id, DEVICE_ID_FOR_CLIENT_1)


def populate_test_devices_esx(axonius_fixture, esx_fixture):
    from parallel_tests.test_esx import client_details, SOME_DEVICE_ID

    client = client_details[0][0]
    assert esx_fixture.is_up()

    client_id = f"{client['host']}/{client['user']}"
    esx_fixture.add_client(client)
    axonius_fixture.assert_device_aggregated(esx_fixture, client_id, SOME_DEVICE_ID)


def check_conf(axonius_fixture, adapter_service, adapter_name):
    adapter = axonius_fixture.db.get_unique_plugin_config(adapter_service.unique_name)
    assert adapter['plugin_name'] == adapter_name
    assert int(adapter[DEVICE_SAMPLE_RATE]) == adapter_service.conf.default_sample_rate
