import os
import pytest
import sys


def main():
    log_path = os.path.join(os.path.dirname(__file__), '..', 'testing', 'reporting', 'deployment_report.xml')
    if not os.path.isdir(os.path.dirname(log_path)):
        os.makedirs(os.path.dirname(log_path))
    return pytest.main(['-x', '-s', '-vv', '--showlocals', '--durations=0', f'--junitxml={log_path}'] + sys.argv)


if __name__ == '__main__':
    sys.exit(main())
