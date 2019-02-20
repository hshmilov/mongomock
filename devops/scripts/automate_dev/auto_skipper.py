#!/usr/bin/env python3
import os
import argparse

ACTUAL_PARENT_FOLDER = os.path.realpath(os.path.dirname(__file__))
BASE_PATH = os.path.realpath(os.path.dirname(os.path.dirname(os.path.dirname(ACTUAL_PARENT_FOLDER))))
TESTING_FOLDER = os.path.join(BASE_PATH, 'testing')
ADAPTER_TESTS_FOLDER = os.path.join(TESTING_FOLDER, 'parallel_tests')
FETCH_DEVICES = '    def test_fetch_devices(self):\n'
NOT_WORKING = 'Not working'
PYTEST_MARK_SKIP = '    @pytest.mark.skip(\'{skipping_reason}\')\n'
IMPORT_PYTEST = 'import pytest\n'
TEST_CHECK_REACHABILITY = '    def test_check_reachability(self):\n'
PASS = '        pass\n'


def main():
    parser = argparse.ArgumentParser(description='Auto skipper')
    parser.add_argument('--adapter', nargs='+', action='append',
                        help='skip a test for adapter')
    parser.add_argument('--ticket', action='store',
                        help='Choose a ticket')

    args = parser.parse_args()

    if args.ticket:
        skipping_line = PYTEST_MARK_SKIP.format(skipping_reason=args.ticket)
    else:
        skipping_line = PYTEST_MARK_SKIP.format(skipping_reason=NOT_WORKING)

    if args.adapter:
        for single_adapter_list in args.adapter:
            single_adapter = single_adapter_list[0]
            adapter_path = os.path.join(ADAPTER_TESTS_FOLDER, f'test_{single_adapter}.py')
            assert os.path.exists(adapter_path), f'No such adapter test: {adapter_path}'
            lines = open(adapter_path, 'r').readlines()

            if IMPORT_PYTEST not in lines:
                lines = [IMPORT_PYTEST] + lines

            if FETCH_DEVICES in lines:
                index = lines.index(FETCH_DEVICES)
                lines = lines[:index] + [skipping_line] + lines[index:]
            else:
                lines = lines + ['\n', skipping_line, FETCH_DEVICES, PASS]

            if TEST_CHECK_REACHABILITY in lines:
                index = lines.index(TEST_CHECK_REACHABILITY)
                lines = lines[:index] + [skipping_line] + lines[index:]
            else:
                lines = lines + ['\n', skipping_line, TEST_CHECK_REACHABILITY, PASS]

            open(adapter_path, 'w').writelines(lines)


if __name__ == '__main__':
    main()
