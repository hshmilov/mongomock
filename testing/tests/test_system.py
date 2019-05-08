import random
import time

import pytest

from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME
from axonius.utils.wait import wait_until
from axonius.consts.system_consts import (CUSTOMER_CONF_PATH,
                                          NODE_CONF_PATH,
                                          NODE_MARKER_PATH,
                                          SYSTEM_CONF_PATH)
from axonius_system import process_exclude_from_config
from devops.axonius_system import main as system_main
from exclude_helper import ExcludeHelper
from services.adapters.infinite_sleep_service import (InfiniteSleepService,
                                                      infinite_sleep_fixture)
from services.adapters.stresstest_scanner_service import (StresstestScanner_fixture,
                                                          StresstestScannerService)
from services.adapters.stresstest_service import (Stresstest_fixture,
                                                  StresstestService)
from test_credentials import test_infinite_sleep_credentials
from test_credentials.test_gui_credentials import DEFAULT_USER
from services.axonius_service import get_service

pytestmark = pytest.mark.sanity
MAX_TIME_FOR_SYNC_RESEARCH_PHASE = 60 * 3  # the amount of time we expect a cycle to end, without async plugins in bg


def test_aggregator_in_configs(axonius_fixture):
    aggregator = axonius_fixture.aggregator
    assert aggregator.version().status_code == 200
    plugin_unique_name = aggregator.unique_name
    aggregator_config = axonius_fixture.db.get_unique_plugin_config(
        plugin_unique_name)
    assert aggregator_config['plugin_name'] == AGGREGATOR_PLUGIN_NAME


def test_aggregator_registered(axonius_fixture):
    aggregator = axonius_fixture.aggregator
    core = axonius_fixture.core
    assert aggregator.is_plugin_registered(core)


def test_aggregator_restart(axonius_fixture):
    axonius_fixture.restart_plugin(axonius_fixture.aggregator)


def test_gui_restart(axonius_fixture):
    axonius_fixture.restart_plugin(axonius_fixture.gui)


def test_core_restart(axonius_fixture):
    axonius_fixture.restart_core()


def test_restart_data_persistency(axonius_fixture):
    test_document = {'Test{0}'.format(random.randint(1, 100)): random.randint(1, 100), 'This': 'Is A Test'}
    axonius_fixture.db.get_collection('test_db', 'test_collection').insert_one(test_document)

    axonius_fixture.db.stop(should_delete=False)
    axonius_fixture.db.start_and_wait()
    test_collection = list(axonius_fixture.db.get_collection('test_db', 'test_collection').find(test_document))

    assert len(test_collection) == 1


def test_system_is_up(axonius_fixture):
    # Waiting to see that all services are up before doing this check
    for service in axonius_fixture.axonius_services:
        service.wait_for_service()


def test_cycle_completes_after_restart(axonius_fixture, StresstestScanner_fixture, Stresstest_fixture):
    scheduler = axonius_fixture.scheduler
    gui = axonius_fixture.gui

    StresstestScanner_fixture.add_client({'device_count': 50, 'name': 'blah'})
    Stresstest_fixture.add_client({'device_count': 50, 'name': 'blah'})

    assert len(StresstestScanner_fixture.clients()) == 1
    assert len(Stresstest_fixture.clients()) == 1

    scheduler.wait_for_scheduler(True)
    scheduler.start_research()
    scheduler.wait_for_scheduler(True)
    wait_until(lambda: scheduler.log_tester.is_str_in_log('Finished Research Phase Successfully.', 10),
               total_timeout=MAX_TIME_FOR_SYNC_RESEARCH_PHASE)

    gui.login_user(DEFAULT_USER)
    devices = gui.get_devices(params={
        'filter': 'adapters == \'stresstest_scanner_adapter\' and adapters == \'stresstest_adapter\''
    }).json()
    assert len(devices) == 50


def test_stop_research(axonius_fixture, infinite_sleep_fixture):
    scheduler = axonius_fixture.scheduler
    infinite_sleep_fixture.add_client(test_infinite_sleep_credentials.client_details)
    assert len(infinite_sleep_fixture.clients()) > 0
    scheduler.start_research()
    scheduler.wait_for_scheduler(False)
    time.sleep(10)  # otherwise the adapter might not even start fetching
    scheduler.stop_research()
    scheduler.wait_for_scheduler(True)


@pytest.mark.skip('AX-3058')
@pytest.mark.parametrize("is_node_mode_test_on", [True, False])
def test_exclude_config(is_node_mode_test_on):
    must_internal_services = []
    system = get_service()
    system.take_process_ownership()
    system.stop(should_delete=True)

    # Two exclusion lists exists:

    # The first exclusion list is purely populated from the config.
    exclude_by_config = ExcludeHelper(SYSTEM_CONF_PATH).process_exclude([])
    exclude_by_config = ExcludeHelper(CUSTOMER_CONF_PATH).process_exclude(exclude_by_config)

    # The second exclusion list is populated by the logic that a node should only run adapters.

    # This list is first populated from system conf even though this list should be by logic because
    # to a few adapters being excluded always throughout the system and we want to get those adapters.
    exclude_by_logic = ExcludeHelper(SYSTEM_CONF_PATH).process_exclude([])

    system_main('system down --all'.split())

    try:
        if is_node_mode_test_on:
            # Adding the case of node to the exclusion lists.
            exclude_by_config = ExcludeHelper(NODE_CONF_PATH).process_exclude(exclude_by_config)
            exclude_by_logic.extend([service_name for service_name, _ in system.get_all_plugins()])
            exclude_by_logic.extend([service.service_name for service in system.axonius_services])

            must_internal_services.extend(['core', 'mongo', 'aggregator'])

            system.start_and_wait(internal_service_white_list=must_internal_services)
            NODE_MARKER_PATH.touch()

        system_main('system up --all'.split())
        for service in system.axonius_services:
            if service.service_name in must_internal_services:
                continue  # These adapters must be up for a basic system to operate.

            if service.service_name in exclude_by_config:
                assert not service.is_up()

            if service.service_name in exclude_by_logic:
                assert not service.is_up()

        for _, adapter in system.get_all_adapters():
            adapter_instance = adapter()
            if adapter_instance.adapter_name not in exclude_by_config:
                assert adapter_instance.is_up()

            if adapter_instance.adapter_name not in exclude_by_logic:
                assert adapter_instance.is_up()
    finally:
        if is_node_mode_test_on and NODE_MARKER_PATH.exists():
            NODE_MARKER_PATH.unlink()


def test_exclude_config_quick():
    try:
        customer_conf = '''
        {
            "exclude-list":
            {
                "add-to-exclude": [], 
                "remove-from-exclude": [ "nimbul" ] 
            }

        }
        '''

        CUSTOMER_CONF_PATH.write_text(customer_conf)
        result = process_exclude_from_config([])
        assert 'nimbul' not in result

    finally:
        if CUSTOMER_CONF_PATH.is_file():
            CUSTOMER_CONF_PATH.unlink()
