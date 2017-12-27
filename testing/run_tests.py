import pytest
import sys


def main():
    return pytest.main(['-x', '-v', '--showlocals', '--junitxml=reporting/integ_report.xml'] + sys.argv)


if __name__ == '__main__':
    sys.exit(main())
