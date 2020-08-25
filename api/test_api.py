# redefined-outer-name is needed since we are defining imported fixtures as var names (ad_fixture, for instance).
# This is a common procedure with pylint and is disabled by default.
# pylint: disable=unused-import, too-many-statements, too-many-locals, redefined-outer-name, too-many-branches
# pylint: disable=no-name-in-module, import-error, invalid-name, global-statement
import time
import logging
import traceback
from multiprocessing.pool import ThreadPool

import pytest

from examples.api_usage import RESTExample
from axonius.utils.wait import wait_until
from axoniussdk.client import RESTClient
from services.adapters.ad_service import ad_fixture
from services.adapters.csv_service import csv_fixture
from services.axonius_service import get_service
from services.plugins.device_control_service import device_control_fixture
from test_credentials.test_ad_credentials import ad_client1_details
from testing.test_credentials.test_gui_credentials import DEFAULT_USER
from testing.tests.conftest import axonius_fixture


logger = logging.getLogger(f'axonius.{__name__}')
MAX_TIME_FOR_SYNC_RESEARCH_PHASE = 60 * 3  # the amount of time we expect a cycle to end, without async plugins in bg


# pylint: disable=redefined-outer-name
@pytest.fixture(scope='module')
def axonius_system(axonius_fixture, device_control_fixture, ad_fixture, csv_fixture):
    axonius_system = get_service()

    ad_fixture.add_client(ad_client1_details)

    axonius_system.scheduler.start_research()
    axonius_system.scheduler.wait_for_scheduler(True)
    wait_until(lambda: axonius_system.scheduler.log_tester.is_str_in_log('Finished Research Phase Successfully.', 10),
               total_timeout=MAX_TIME_FOR_SYNC_RESEARCH_PHASE)

    return axonius_system


ERROR = False
PROBLEMS = []


# We don't want to run this for the meanwhile
def _test_api(axonius_system):
    client = RESTExample('https://127.0.0.1',
                         auth=(DEFAULT_USER['user_name'], DEFAULT_USER['password']),
                         verify=False)

    for name in client.get_examples():
        logger.info(f'Calling api function "{name}"')
        callback = getattr(client, name)
        callback()
        logger.info('\n\n')


def test_api_in_parallel(axonius_system):
    client = RESTExample('https://127.0.0.1',
                         auth=(DEFAULT_USER['user_name'], DEFAULT_USER['password']),
                         verify=False)

    def run_specific_configuration(client, name):
        try:
            global ERROR
            if ERROR:
                # we don't need to run more tests since we already failed
                return
            logger.info(f'Calling api function "{name}"')
            start_time = time.time()
            callback = getattr(client, name)
            callback()
            logger.info(f'Finished calling function "{name}" in "{time.time() - start_time}" seconds.')
            logger.info('\n\n')
        except Exception:
            ERROR = True
            logger.exception(None)
            print(f'Error in in test_api for name {name}: \n {traceback.format_exc()}')
            PROBLEMS.append(name)
            raise

    to_run = ((client, name)
              for name in client.get_examples())

    with ThreadPool(50) as pool:
        pool.starmap_async(run_specific_configuration, to_run).wait(timeout=60 * 60 * 3)

    global ERROR
    assert not ERROR, PROBLEMS
