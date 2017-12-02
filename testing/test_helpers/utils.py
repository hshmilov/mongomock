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


def populate_test_devices(axonius_fixture):
    from tests import test_ad
    from services.ad_service import AdService

    ad_adapter = AdService()
    client_id = test_ad.ad_client_details['dc_name']
    if not ad_adapter.is_up():
        ad_adapter.start_and_wait()

    axonius_fixture.add_client_to_adapter(ad_adapter, test_ad.ad_client_details, client_id)
