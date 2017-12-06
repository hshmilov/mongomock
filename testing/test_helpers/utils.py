import time


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
    from tests.test_ad import ad_client1_details, DEVICE_ID_FOR_CLIENT_1

    client_id = ad_client1_details['dc_name']
    assert ad_fixture.is_up()

    axonius_fixture.add_client_to_adapter(ad_fixture, ad_client1_details)
    axonius_fixture.assert_device_aggregated(ad_fixture, client_id, DEVICE_ID_FOR_CLIENT_1)
