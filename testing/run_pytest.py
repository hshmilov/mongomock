import os
import sys
import time

from typing import List, AnyStr

import pytest

LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
VALID_RC_FOR_PYTEST = [0, 1]  # https://docs.pytest.org/en/latest/usage.html#possible-exit-codes


def run_pytest(pytest_args: List[AnyStr]):
    """
    Runs pytest on the given test paths
    :param pytest_args: a list of paths or additional arguments to pytest
    :return:
    """
    xml_file = '_'.join([arg for arg in pytest_args if not arg.startswith('-')])\
        .replace('./', '').replace(' ', '_').replace('/', '_').replace('\\', '_').replace('-', '_').replace('=', '_')\
        .replace('::', '_')
    xml_file = f'{xml_file}.xml' if xml_file else f'{time.time()}.xml'
    xml_file = os.path.join(LOGS_DIR, xml_file)

    rc = pytest.main(
        [
            '--junitxml', os.path.join(LOGS_DIR, xml_file),
            '-s',
            '-vv',
            '--showlocals',
            '--durations=0'
        ] + pytest_args
    )

    if rc not in VALID_RC_FOR_PYTEST:
        sys.stderr.write(f'pytest returned value {rc} which is not in the valid values of pytest')
        exit(rc)


if __name__ == '__main__':
    sys.exit(run_pytest(sys.argv[1:]))
