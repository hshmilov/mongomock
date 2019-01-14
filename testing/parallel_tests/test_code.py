import glob
import multiprocessing
import os
import signal
import subprocess
import sys

import pytest

pytestmark = pytest.mark.sanity

NUMBER_OF_PROCESSES = 3
GOOD_EXIT_CODE = 0
EXCLUDE_PATHS = [
    'devops',
    'logs',
    'venv',
    'usr',
    '.idea',
    '.git',
    '.venv'
]
ACTUAL_PARENT_FOLDER = os.path.realpath(os.path.dirname(__file__))
ABSOLUTE_ROOT_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..')
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
            if name.endswith('.py') and not _file_name_in_excluded_paths(BASE_PATH, fullname):
                yield fullname


def _get_pylint_path():
    which_command = 'which'
    if sys.platform == 'win32':
        which_command = 'where'
    return subprocess.Popen([which_command, 'pylint'], stdout=subprocess.PIPE).communicate()[0].decode('utf-8').strip()


def _is_pylint_ok_expected_true(file_name):
    return _is_pylint_ok(file_name, True)


def _is_pylint_ok_expected_false(file_name):
    return _is_pylint_ok(file_name, False)


def _is_pylint_ok(file_name, is_success_expected):
    pylint_path = _get_pylint_path()
    child = subprocess.Popen(
        [pylint_path, '--rcfile', PYLINTRC_FILE, file_name],
        stdout=subprocess.PIPE)
    stdout, stderr = child.communicate()
    decoded = stdout.decode('utf-8')
    good_file = child.returncode == GOOD_EXIT_CODE and \
        any(report in decoded for report in (PERFECT_PYLINT_MESSAGE, PYLINT_EMPTY_FILE))
    if not good_file and is_success_expected:
        sys.stderr.write(f'ERROR: Found bad pylinted file {file_name}')
        sys.stderr.write(decoded)
    return file_name, good_file, f'{good_file}:\n{decoded}'


def _get_file_content(file_name):
    with open(file_name, 'rb') as file_handler:
        return file_handler.read()


def _is_file_empty(path):
    return os.stat(path).st_size == 0


def _get_all_pylint_files():
    if not hasattr(_get_all_pylint_files, 'all_pylint_files'):
        _get_all_pylint_files.all_pylint_files = [
            file_name
            for file_name
            in _get_all_files()
            if not file_name.startswith('/usr/lib') and 'splunklib' not in file_name and not _is_file_empty(file_name)
        ]

    return _get_all_pylint_files.all_pylint_files


def _get_single_exempt_path(file_name):
    path = os.path.join(BASE_PATH, file_name.decode('utf-8').rstrip())
    return os.path.realpath(path)


def _get_pylint_exempt():
    if not hasattr(_get_pylint_exempt, 'pylint_exempt'):
        with open(PYLINT_EXEMPT_FILE_NAME, 'rb') as f:
            _get_pylint_exempt.pylint_exempt = [
                _get_single_exempt_path(file_name)
                for file_name
                in f.readlines()
            ]

    return _get_pylint_exempt.pylint_exempt


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
        # we do this hassle because we can't pickle lambdas
        func = _is_pylint_ok_expected_true if is_success_expected else _is_pylint_ok_expected_false
        res = process_pool.map_async(func, files_to_map)  # return tuple
        mapped_values = res.get(60 * 20)
    except KeyboardInterrupt:
        process_pool.terminate()
        process_pool.join()
        raise AssertionError('manually terminated')

    process_pool.close()
    process_pool.join()

    return [(item[0], item[2]) for item in mapped_values if is_success_expected != item[1]]


class TestCode:
    @staticmethod
    def test_no_broken_pylint_files():
        """Test that every file besides the ones in the exempt list pass pylint"""
        broken_files_list = _get_unexpected_pylint_state(is_success_expected=True)
        invalid_files = bool(broken_files_list)
        assert not invalid_files, \
            'Broken files found: {}'.format('\n'.join([file_desc[1] for file_desc in broken_files_list]))

    @staticmethod
    def test_no_proper_files_in_exempt_list():
        """Test that every file in the exempt list does not pass pylint"""
        exempted_proper_files = _get_unexpected_pylint_state(
            is_success_expected=False)
        invalid_files = bool(exempted_proper_files)
        assert not invalid_files, 'Proper files found in exempt list: Please remove {} from {}'.format(
            '\n'.join([files[0] for files in exempted_proper_files]), PYLINT_EXEMPT_FILE_NAME)

    @staticmethod
    def test_formatting():
        child = subprocess.Popen(
            ['/bin/bash', '-c', 'git ls-files | grep "\\.py" | xargs autopep8 --max-line-length 120 --diff'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ABSOLUTE_ROOT_DIR
        )
        stdout, stderr = child.communicate(timeout=60 * 5)
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        assert child.returncode == 0, f'Return code is {child.returncode}\nstdout:\n{stdout}stderr:\n{stderr}'
        assert not stdout.strip(), f'Code is not formatted!\n{stdout}'
        assert not stderr.strip(), f'Code is not formatted!\n{stderr}'

    @staticmethod
    def test_bare_except():
        child = subprocess.Popen(
            ['/bin/bash', '-c', 'git ls-files | grep "\\.py" | xargs autopep8 --select=E722 --diff -a'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ABSOLUTE_ROOT_DIR
        )
        stdout, stderr = child.communicate(timeout=60 * 5)
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        assert child.returncode == 0, f'Return code is {child.returncode}\nstdout:\n{stdout}stderr:\n{stderr}'
        assert not stdout.strip(), f'Code contains "except:"!\n{stdout}'
        assert not stderr.strip(), f'Code contains "except:"!\n{stderr}'

    @staticmethod
    def test_crlf():
        child = subprocess.Popen(
            ['/bin/bash', '-c',
             'git ls-files | grep -E "(\\.py|\\.sh|\\.yml|Dockerfile)" | xargs grep $(printf "\r") -r'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ABSOLUTE_ROOT_DIR
        )
        stdout, stderr = child.communicate(timeout=60 * 5)
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        # 123 is a legitimate value since if we do not have any bad files then xargs will return 123
        assert child.returncode in [0, 123], f'Return code is {child.returncode}\nstdout:\n{stdout}stderr:\n{stderr}'
        assert not stdout.strip(), f'CRLF found!\n{stdout}'
        assert not stderr.strip(), f'CRLF found!\n{stderr}'

    @staticmethod
    def test_requirements_files():
        bad_lines = []
        for file_path in glob.iglob(os.path.join(BASE_PATH, '**', 'requirements*.txt'), recursive=True):
            with open(file_path, 'rt') as file:
                for line in file.readlines():
                    if '==' not in line:
                        bad_lines.append(f'{file_path}: found line with no "==": {line}')

        bad_lines = '\n'.join(bad_lines)
        assert not bad_lines, f'Found requirements.txt files with "==": \n{bad_lines}'
