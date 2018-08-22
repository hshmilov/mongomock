import multiprocessing
import os
import signal
import subprocess
import sys

import pytest

pytestmark = pytest.mark.sanity

NUMBER_OF_PROCESSES = 12
GOOD_EXIT_CODE = 0
EXCLUDE_PATHS = [
    'devops',
    'logs',
    'venv',
    'usr',
    '.idea',
    '.git',
    '.venv',
    os.path.join('adapters', 'splunk_nexpose_adapter', 'external')
]
ACTUAL_PARENT_FOLDER = os.path.realpath(os.path.dirname(__file__))
BASE_PATH = os.path.realpath(os.path.dirname(os.path.dirname(ACTUAL_PARENT_FOLDER)))
PYLINT_EXEMPT_FILE_NAME = os.path.join(ACTUAL_PARENT_FOLDER, 'pylint_exempt_list.txt')
PYLINTRC_FILE = os.path.join(BASE_PATH, 'pylintrc.txt')
PERFECT_PYLINT_MESSAGE = 'Your code has been rated at 10.00/10'
PYLINT_EMPTY_FILE = '0 statements analysed.'


def _file_name_in_excluded_paths(base_path, file_name):
    return any(file_name.startswith(os.path.join(base_path, exclude))
               for exclude
               in EXCLUDE_PATHS)


def _get_all_files():
    for path, subdirs, files in os.walk(BASE_PATH):
        for name in files:
            fullname = os.path.realpath(os.path.join(path, name))
            if _file_name_in_excluded_paths(BASE_PATH, fullname):
                continue
            if name.endswith('.py'):
                yield fullname


def _get_pylint_path():
    which_command = 'which'
    if sys.platform == 'win32':
        which_command = 'where'
    return subprocess.Popen([which_command, 'pylint'], stdout=subprocess.PIPE).communicate()[0].decode('utf-8').strip()


def _is_pylint_ok(file_name):
    pylint_path = _get_pylint_path()
    child = subprocess.Popen(
        [pylint_path, '--rcfile', PYLINTRC_FILE, file_name],
        stdout=subprocess.PIPE)
    stdout, stderr = child.communicate()
    decoded = stdout.decode('utf-8')
    good_file = child.returncode == GOOD_EXIT_CODE and \
        any(report in decoded for report in (PERFECT_PYLINT_MESSAGE, PYLINT_EMPTY_FILE))
    return file_name, good_file


def _get_file_content(file_name):
    with open(file_name, 'rb') as file_handler:
        return file_handler.read()


def _get_all_pylint_files():
    return [
        file_name
        for file_name
        in _get_all_files()
        if not file_name.startswith('/usr/lib') and 'splunklib' not in file_name
    ]


def _get_single_exempt_path(file_name):
    path = os.path.join(BASE_PATH, file_name.decode('utf-8').rstrip())
    return os.path.realpath(path)


def _get_pylint_exempt():
    with open(PYLINT_EXEMPT_FILE_NAME, 'rb') as f:
        return [
            _get_single_exempt_path(file_name)
            for file_name
            in f.readlines()
        ]


def _get_unexpected_pylint_state(is_success_expected):
    files_to_map = [
        file_name
        for file_name
        in _get_all_pylint_files()
        if (file_name in _get_pylint_exempt()) != is_success_expected
    ]
    # We do this in order to be able to kill the forks using KeyboardInterrupt
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    process_pool = multiprocessing.Pool(NUMBER_OF_PROCESSES)
    signal.signal(signal.SIGINT, original_sigint_handler)
    try:
        res = process_pool.map_async(_is_pylint_ok, files_to_map)  # return tuple
        mapped_values = res.get(60 * 20)
    except KeyboardInterrupt:
        process_pool.terminate()
        process_pool.join()
        raise AssertionError('manually terminated')

    process_pool.close()
    process_pool.join()

    return [item[0] for item in mapped_values if is_success_expected != item[1]]


class TestCode:
    @staticmethod
    def test_no_broken_pylint_files():
        """Test that every file besides the ones in the exempt list pass pylint"""
        broken_files = _get_unexpected_pylint_state(is_success_expected=True)
        invalid_files = bool(broken_files)
        assert not invalid_files, 'Broken files found: {}'.format('\n'.join(broken_files))

    @staticmethod
    def test_no_proper_files_in_exempt_list():
        """Test that every file in the exempt list does not pass pylint"""
        exempted_proper_files = _get_unexpected_pylint_state(
            is_success_expected=False)
        invalid_files = bool(exempted_proper_files)
        assert not invalid_files, 'Proper files found in exempt list: Please remove {} from {}'.format(
            '\n'.join(exempted_proper_files), PYLINT_EXEMPT_FILE_NAME)
