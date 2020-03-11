import json
import re

from axonius.consts.system_consts import LOGS_PATH_HOST
from axonius.utils.wait import wait_until
from services.plugins.diagnostics_service import DiagnosticsService
from test_credentials.test_reverse_ssh_creds import (TEST_STUNNEL_CREDS, TEST_PROXY_STRING)
from test_helpers.log_tester import LogTester

SUCCESS_LOG_1 = 'Allocated port .* for remote forward to localhost:22'
SUCCESS_LOG_PROXY = re.escape('connect_blocking: connected 10.0.230.207:8888')


def test_no_proxy():
    diag = DiagnosticsService()
    diag_env_file = diag.diag_env_file
    diag_env_file.write_text(json.dumps(TEST_STUNNEL_CREDS))
    with diag.contextmanager(take_ownership=True):
        docker_log = LogTester(LOGS_PATH_HOST / 'diagnostics' / 'diagnostics.docker.log')
        wait_until(lambda: docker_log.is_pattern_in_log(SUCCESS_LOG_1, 1), tolerated_exceptions_list=[Exception])


def test_with_proxy():
    diag = DiagnosticsService()
    diag_env_file = diag.diag_env_file
    creds = TEST_STUNNEL_CREDS.copy()
    creds['HTTPS_PROXY'] = TEST_PROXY_STRING
    diag_env_file.write_text(json.dumps(creds))
    with diag.contextmanager(take_ownership=True):
        docker_log = LogTester(LOGS_PATH_HOST / 'diagnostics' / 'diagnostics.docker.log')
        wait_until(lambda: docker_log.is_pattern_in_log(SUCCESS_LOG_PROXY, 10), tolerated_exceptions_list=[Exception])
        wait_until(lambda: docker_log.is_pattern_in_log(SUCCESS_LOG_1, 3), tolerated_exceptions_list=[Exception])
