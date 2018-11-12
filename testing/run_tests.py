import pytest
import sys


def main():
    return pytest.main(['-s', '-vv', '--showlocals', '--durations=0'] + sys.argv)


if __name__ == '__main__':
    sys.exit(main())
