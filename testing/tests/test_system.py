import random

from retrying import retry

from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME
from axonius.consts.scheduler_consts import StateLevels, Phases
from services.adapters.infinite_sleep_service import InfiniteSleepService, infinite_sleep_fixture
from test_credentials import test_infinite_sleep_credentials


def test_stop_research(axonius_fixture, infinite_sleep_fixture):
    @retry(stop_max_attempt_number=100, wait_fixed=1000, retry_on_result=lambda result: result is False)
    def _wait_for_state(scheduler, cond):
        state = scheduler.current_state().json()
        return (state[StateLevels.Phase.name] == Phases.Stable.name) == cond
    scheduler = axonius_fixture.scheduler
    core = axonius_fixture.core
    aggregator = axonius_fixture.aggregator
    assert scheduler.is_up()
    assert aggregator.is_up()
    assert infinite_sleep_fixture.is_up()
    infinite_sleep_fixture.add_client(test_infinite_sleep_credentials.client_details)
    assert len(infinite_sleep_fixture.clients()) > 0
    scheduler.start_research()
    _wait_for_state(scheduler, False)
    scheduler.stop_research()
    _wait_for_state(scheduler, True)


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


def test_plugin_state_change(axonius_fixture):
    execution = axonius_fixture.execution
    # Check initial state
    execution.assert_plugin_state('enabled')
    # Change state
    assert execution.post('/plugin_state?wanted=disable').status_code == 200
    # Check disabled
    execution.assert_plugin_state('disabled')
    # Restart plugin
    axonius_fixture.restart_plugin(axonius_fixture.execution)
    # Check disabled
    execution.assert_plugin_state('disabled')
    # Change back to enabled
    assert execution.post('/plugin_state?wanted=enable').status_code == 200
    # Check enabled
    execution.assert_plugin_state('enabled')
    # Restart plugin
    axonius_fixture.restart_plugin(axonius_fixture.execution)
    # Check enabled
    execution.assert_plugin_state('enabled')


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
    assert axonius_fixture.db.is_up()
    assert axonius_fixture.core.is_up()
    assert axonius_fixture.aggregator.is_up()
