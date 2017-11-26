import pytest
import sys

filtering = sys.argv[1] if len(sys.argv) == 2 else ""


def main():
    return pytest.main(['-s', './tests' + filtering])


if __name__ == '__main__':
    sys.exit(main())
