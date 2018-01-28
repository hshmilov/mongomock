import pytest
import sys


def main():
    return pytest.main(['-x', '-v', '--showlocals', '--full-trace', '--durations=0', '--junitxml=reporting/integ_report.xml'] + sys.argv)


if __name__ == '__main__':
    sys.exit(main())
