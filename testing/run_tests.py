import pytest
import sys


def main():
    return pytest.main(['-s', './tests'])


if __name__ == '__main__':
    sys.exit(main())
