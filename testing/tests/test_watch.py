import pytest
from bson.objectid import ObjectId
import datetime
import time

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from services.watch_service import watch_fixture

NO_RESULT_WATCH_DB_DOC = {
    "alert_types": [
        {
            "message": "First Watch triggered",
            "title": "first watch triggered!",
            "type": "notification"
        }
    ],
    "criteria": 0,
    "query": "{\"adapters\": {\"$elemMatch\": {\"data.name\": \"DESKTOP-MPP10U1\"}}}",
    "query_sample_rate": 10,
    "result": [],
    "retrigger": True,
    "triggsered": True,
    "watch_time": "Mon, 20 Nov 2017 13:18:16 GMT"
}

WATCH = {
    "query": {"adapters": {"$elemMatch": {"data.name": "DESKTOP-MPP10U1"}}},
    "criteria": 0,
    "retrigger": False,
    "name": "test watch",
    "severity": "Worse",
    "alert_types": [
        {
            "message": "First Watch triggered",
            "title": "first watch triggered!",
            "type": "notification"
        }
    ],
}

DEVICE_ONE = {'accurate_for_datetime': datetime.datetime(2017, 11, 19, 13, 21, 55, 378000),
              'adapters': [
                  {'accurate_for_datetime': datetime.datetime(2017, 11, 19, 13, 21, 55, 378000),
                   'client_used': '10.0.229.30',
                   'data': {'id': 'CN=DESKTOP-123123,CN=Computers,DC=TestDomain,DC=test',
                            'name': 'DESKTOP-MPP10U1',
                            'os': {'bitness': None, 'distribution': '10', 'type': 'Windows'},
                            'pretty_id': 'pretty_id_1',
                            'raw': {'accountExpires': 'Fri, 31 Dec 9999 23:59:59 GMT',
                                    'badPasswordTime': 'Mon, 01 Jan 1601 00:00:00 GMT',
                                    'badPwdCount': 0,
                                    'cn': 'DESKTOP-123',
                                    'codePage': 0,
                                    'countryCode': 0,
                                    'dNSHostName': 'DESKTOP-MPP10U1.TestDomain.test',
                                    'dSCorePropagationData': ['Mon, 01 Jan 1601 00:00:00 GMT'],
                                    'distinguishedName': 'CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test',
                                    'instanceType': 4,
                                    'isCriticalSystemObject': False,
                                    'lastLogoff': 'Mon, 01 Jan 1601 00:00:00 GMT',
                                    'lastLogon': 'Thu, 16 Nov 2017 13:14:24 GMT',
                                    'lastLogonTimestamp': 'Mon, 06 Nov 2017 14:15:21 GMT',
                                    'localPolicyFlags': 0,
                                    'logonCount': 64,
                                    'msDS-SupportedEncryptionTypes': 28,
                                    'name': 'DESKTOP-MPP10U1',
                                    'objectCategory': 'CN=Computer,CN=Schema,CN=Configuration,DC=TestDomain,DC=test',
                                    'objectClass': ['top',
                                                    'person',
                                                    'organizationalPerson',
                                                    'user',
                                                    'computer'],
                                    'objectGUID': 'f9ab6ae1-1f67-465a-9d75-2e97d06b6453',
                                    'objectSid': 'S-1-5-21-4050441107-50035988-2732102988-1103',
                                    'operatingSystem': 'Windows 10 Pro',
                                    'operatingSystemVersion': '10.0 (15063)',
                                    'primaryGroupID': 515,
                                    'pwdLastSet': 'Mon, 06 Nov 2017 14:15:18 GMT',
                                    'sAMAccountName': 'DESKTOP-MPP10U1$',
                                    'sAMAccountType': 805306369,
                                    'servicePrincipalName': [
                                        'RestrictedKrbHost/DESKTOP-MPP10U1',
                                        'HOST/DESKTOP-MPP10U1',
                                        'RestrictedKrbHost/DESKTOP-MPP10U1.TestDomain.test',
                                        'HOST/DESKTOP-MPP10U1.TestDomain.test'],
                                    'uSNChanged': 12833,
                                    'uSNCreated': 12816,
                                    'userAccountControl': 4096,
                                    'whenChanged': 'Mon, 06 Nov 2017 14:16:42 GMT',
                                    'whenCreated': 'Mon, 06 Nov 2017 14:15:18 GMT'}},
                   'plugin_name': 'ad_adapter',
                   'plugin_type': 'Adapter',
                   PLUGIN_UNIQUE_NAME: 'ad_adapter_1'}
],
    'internal_axon_id': '6990cbe1410f4826886e542b82459b5a',
    'tags': []}
DEVICE_TWO = {'accurate_for_datetime': datetime.datetime(2017, 11, 19, 13, 21, 55, 380000),
              'adapters': [
                  {'_id': ObjectId('5a118573861256000131ad31'),
                   'accurate_for_datetime': datetime.datetime(2017, 11, 19, 13, 21, 55, 380000),
                   'client_used': '10.0.229.30',
                   'data': {'id': 'CN=WINDOWS8,CN=Computers,DC=TestDomain,DC=test',
                            'name': 'DESKTOP-MPP10U1',
                            'os': {'bitness': None, 'distribution': '8', 'type': 'Windows'},
                            'pretty_id': 'pretty_id_2',
                            'raw': {'accountExpires': 'Fri, 31 Dec 9999 23:59:59 GMT',
                                    'badPasswordTime': 'Mon, 01 Jan 1601 00:00:00 GMT',
                                    'badPwdCount': 0,
                                    'cn': 'WINDOWS8',
                                    'codePage': 0,
                                    'countryCode': 0,
                                    'dNSHostName': 'windows8.TestDomain.test',
                                    'dSCorePropagationData': ['Mon, 01 Jan 1601 00:00:00 GMT'],
                                    'distinguishedName': 'CN=WINDOWS8,CN=Computers,DC=TestDomain,DC=test',
                                    'instanceType': 4,
                                    'isCriticalSystemObject': False,
                                    'lastLogoff': 'Mon, 01 Jan 1601 00:00:00 GMT',
                                    'lastLogon': 'Mon, 06 Nov 2017 22:03:05 GMT',
                                    'lastLogonTimestamp': 'Mon, 06 Nov 2017 14:40:55 GMT',
                                    'localPolicyFlags': 0,
                                    'logonCount': 3,
                                    'msDS-SupportedEncryptionTypes': 28,
                                    'name': 'WINDOWS8',
                                    'objectCategory': 'CN=Computer,CN=Schema,CN=Configuration,DC=TestDomain,DC=test',
                                    'objectClass': ['top',
                                                    'person',
                                                    'organizationalPerson',
                                                    'user',
                                                    'computer'],
                                    'objectGUID': '68fab94e-9512-4493-b8be-6ccc86a7370c',
                                    'objectSid': 'S-1-5-21-4050441107-50035988-2732102988-1104',
                                    'operatingSystem': 'Windows 8.1 Enterprise',
                                    'operatingSystemVersion': '6.3 (9600)',
                                    'primaryGroupID': 515,
                                    'pwdLastSet': 'Mon, 06 Nov 2017 14:40:19 GMT',
                                    'sAMAccountName': 'WINDOWS8$',
                                    'sAMAccountType': 805306369,
                                    'servicePrincipalName': ['RestrictedKrbHost/WINDOWS8',
                                                             'HOST/WINDOWS8',
                                                             'RestrictedKrbHost/windows8.TestDomain.test',
                                                             'HOST/windows8.TestDomain.test'],
                                    'uSNChanged': 12854,
                                    'uSNCreated': 12846,
                                    'userAccountControl': 4096,
                                    'whenChanged': 'Mon, 06 Nov 2017 14:40:58 GMT',
                                    'whenCreated': 'Mon, 06 Nov 2017 14:40:19 GMT'}},
                   'plugin_name': 'ad_adapter',
                   'plugin_type': 'Adapter',
                   PLUGIN_UNIQUE_NAME: 'ad_adapter_1'}
],
    'internal_axon_id': 'aca32b5ab07042c3aa55a484eb419bad',
    'tags': []}

AGGREGATOR_UNIQUE_NAME = None


@pytest.mark.skip
def test_valid_watch_creation(axonius_fixture, watch_fixture):
    num_of_watches = len(list(axonius_fixture.db.get_collection(watch_fixture.unique_name, 'watches').find()))
    response = watch_fixture.create_watch(WATCH)
    assert response.status_code == 201
    assert len(list(axonius_fixture.db.get_collection(
        watch_fixture.unique_name, 'watches').find())) == num_of_watches + 1


@pytest.mark.skip
def test_invalid_watch_creation(axonius_fixture, watch_fixture):
    num_of_watches = len(list(axonius_fixture.db.get_collection(watch_fixture.unique_name, 'watches').find()))
    response = watch_fixture.create_watch('blah')
    assert response.json()['message'] == 'Expected JSON, got something else...'
    assert len(list(axonius_fixture.db.get_collection(watch_fixture.unique_name, 'watches').find())) == num_of_watches


@pytest.mark.skip
def test_duplicate_watch_creation(axonius_fixture, watch_fixture):
    num_of_watches = len(list(axonius_fixture.db.get_collection(watch_fixture.unique_name, 'watches').find()))
    response = watch_fixture.create_watch(WATCH)
    assert response.status_code == 409
    assert len(list(axonius_fixture.db.get_collection(watch_fixture.unique_name, 'watches').find())) == num_of_watches


@pytest.mark.skip
def test_valid_watch_deletion(axonius_fixture, watch_fixture):
    num_of_watches = len(list(axonius_fixture.db.get_collection(watch_fixture.unique_name, 'watches').find()))
    watch_fixture.delete_watch(WATCH)
    assert len(list(axonius_fixture.db.get_collection(
        watch_fixture.unique_name, 'watches').find())) == num_of_watches - 1


@pytest.mark.skip
def test_non_existing_watch_deletion(axonius_fixture, watch_fixture):
    new_watch = dict(WATCH)

    new_watch['query'] = {'_id': 'Blah'}
    new_watch['criteria'] = -1
    new_watch["name"] = "Not Here"
    new_watch["alert_types"] = []
    response = watch_fixture.delete_watch(WATCH)
    assert response.status_code == 404


@pytest.mark.skip
def test_bad_watch_deletion(axonius_fixture, watch_fixture):
    response = watch_fixture.delete_watch('bad request')
    assert response.status_code == 400


@pytest.mark.skip("Needs a clear function.")
def test_empty_watch_list(axonius_fixture, watch_fixture):
    response = watch_fixture.get_watches()
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.skip
def test_full_watches_list(axonius_fixture, watch_fixture):
    watch_fixture.create_watch(WATCH)
    response = watch_fixture.get_watches()
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]['query'] == NO_RESULT_WATCH_DB_DOC['query']
    assert response.json()[0]['alert_types'] == NO_RESULT_WATCH_DB_DOC['alert_types']
    watch_fixture.delete_watch(WATCH)


def _make_sure_aggregator_is_down(axonius_fixture):
    global AGGREGATOR_UNIQUE_NAME
    if AGGREGATOR_UNIQUE_NAME is None:
        AGGREGATOR_UNIQUE_NAME = axonius_fixture.aggregator.unique_name
    aggregator_unique_name = AGGREGATOR_UNIQUE_NAME
    axonius_fixture.aggregator.stop()
    axonius_fixture.get_devices_db().drop()

    return aggregator_unique_name


@pytest.mark.skip
def test_positive_criteria_trigger(axonius_fixture, watch_fixture):
    aggregator_unique_name = _make_sure_aggregator_is_down(axonius_fixture)

    # Add a positive watch
    WATCH['criteria'] = 1
    watch_fixture.create_watch(WATCH)

    # Add device
    axonius_fixture.get_devices_db().insert_one(DEVICE_ONE)

    # Wait to see new notifications are created by watch
    wait_for_notification(watch_fixture, axonius_fixture.db.get_collection('core', 'notifications'),
                          WATCH['alert_types'][0])

    assert watch_fixture.get_watches().json()[0]['triggered'] == 1

    axonius_fixture.get_devices_db().insert_one(DEVICE_TWO)

    try:
        # Wait to see no new notifications are created by watch
        wait_for_notification(watch_fixture, axonius_fixture.db.get_collection('core', 'notifications'),
                              WATCH['alert_types'][0])
    except Exception as err:
        assert err.args[0] == 'Was not notified'

    watch_fixture.delete_watch(WATCH)

    axonius_fixture.get_devices_db().drop()


@pytest.mark.skip
def test_negative_criteria_trigger(axonius_fixture, watch_fixture):
    aggregator_unique_name = _make_sure_aggregator_is_down(axonius_fixture)

    # Add a negative watch
    WATCH['criteria'] = -1
    WATCH['alert_types'][0]['title'] = 'Another Watch'
    # Add devices
    axonius_fixture.get_devices_db().insert_one(DEVICE_ONE)
    axonius_fixture.get_devices_db().insert_one(DEVICE_TWO)

    watch_fixture.create_watch(WATCH)

    # Remove device.
    axonius_fixture.get_devices_db().delete_one(WATCH['query'])

    # Wait to see new notifications are created by watch
    wait_for_notification(watch_fixture, axonius_fixture.db.get_collection('core', 'notifications'),
                          WATCH['alert_types'][0])

    assert watch_fixture.get_watches().json()[0]['triggered'] == 1

    # Remove another device
    axonius_fixture.get_devices_db().delete_one(WATCH['query'])

    try:
        # Wait to see no new notifications are created by watch
        wait_for_notification(watch_fixture, axonius_fixture.db.get_collection('core', 'notifications'),
                              WATCH['alert_types'][0])
    except Exception as err:
        assert err.args[0] == 'Was not notified'

    watch_fixture.delete_watch(WATCH)

    axonius_fixture.get_devices_db().drop()


@pytest.mark.skip
def test_any_criteria_trigger(axonius_fixture, watch_fixture):
    aggregator_unique_name = _make_sure_aggregator_is_down(axonius_fixture)

    # Add a negative watch
    WATCH['criteria'] = 0
    WATCH['alert_types'][0]['title'] = 'Last Watch'
    watch_fixture.create_watch(WATCH)

    # Check no devices are in the DB
    assert len(list(
        axonius_fixture.get_devices_db().find(WATCH['query']))) == 0

    # Add device
    axonius_fixture.get_devices_db().insert_one(DEVICE_ONE)

    # Wait to see new notifications are created by watch
    wait_for_notification(watch_fixture, axonius_fixture.db.get_collection('core', 'notifications'),
                          WATCH['alert_types'][0])

    assert watch_fixture.get_watches().json()[0]['triggered'] == 1

    # Refresh watch
    watch_fixture.delete_watch(WATCH)
    watch_fixture.create_watch(WATCH)

    # Remove device
    axonius_fixture.get_devices_db().delete_one(WATCH['query'])

    # Wait to see new notifications are created by watch
    wait_for_notification(watch_fixture, axonius_fixture.db.get_collection('core', 'notifications'),
                          WATCH['alert_types'][0])

    watch_fixture.delete_watch(WATCH)

    axonius_fixture.get_devices_db().drop()


@pytest.mark.skip
def test_retrigger_one_change(axonius_fixture, watch_fixture):
    aggregator_unique_name = _make_sure_aggregator_is_down(axonius_fixture)

    WATCH['retrigger'] = True
    # Add a positive watch
    WATCH['criteria'] = 1
    watch_fixture.create_watch(WATCH)

    # Add device
    axonius_fixture.get_devices_db().insert_one(DEVICE_ONE)

    # Wait to see new notifications are created by watch
    wait_for_notification(watch_fixture, axonius_fixture.db.get_collection('core', 'notifications'),
                          WATCH['alert_types'][0])

    assert watch_fixture.get_watches().json()[0]['triggered'] == 1

    try:
        # Wait to see new notifications are created by watch
        wait_for_notification(watch_fixture, axonius_fixture.db.get_collection('core', 'notifications'),
                              WATCH['alert_types'][0])
    except Exception as err:
        assert err.args[0] == 'Was not notified'

    watch_fixture.delete_watch(WATCH)

    # Remove device
    axonius_fixture.get_devices_db().delete_one(WATCH['query'])

    axonius_fixture.get_devices_db().drop()


@pytest.mark.skip
def test_retrigger_multiple_changes(axonius_fixture, watch_fixture):
    aggregator_unique_name = _make_sure_aggregator_is_down(axonius_fixture)

    WATCH['retrigger'] = True
    # Add a positive watch
    WATCH['criteria'] = 0
    watch_fixture.create_watch(WATCH)

    # Add device
    axonius_fixture.get_devices_db().insert_one(DEVICE_ONE)

    # Wait to see new notifications are created by watch
    wait_for_notification(watch_fixture, axonius_fixture.db.get_collection('core', 'notifications'),
                          WATCH['alert_types'][0])

    assert watch_fixture.get_watches().json()[0]['triggered'] == 1

    axonius_fixture.get_devices_db().insert_one(
        DEVICE_TWO)

    # Wait to see new notifications are created by watch
    wait_for_notification(watch_fixture, axonius_fixture.db.get_collection('core', 'notifications'),
                          WATCH['alert_types'][0])

    assert watch_fixture.get_watches().json()[0]['triggered'] == 2

    watch_fixture.delete_watch(WATCH)

    axonius_fixture.get_devices_db().drop()


def wait_for_notification(watch_fixture, notification_db, notification, interval=5, num_intervals=3):
    def got_notified(starting_num_of_notifications):
        return len(list(notification_db.find({'title': notification['title']}))) == starting_num_of_notifications + 1

    curent_num_of_notifications = len(list(notification_db.find({'title': notification['title']})))
    success = False
    for x in range(1, num_intervals):
        try:
            watch_fixture.run_jobs()
            assert got_notified(curent_num_of_notifications)
            success = True
            break
        except:
            time.sleep(interval)

    if not success:
        raise Exception("Was not notified")


@pytest.mark.skip("Needs to do.")
def test_watch_restart(axonius_fixture, watch_fixture):
    pass
