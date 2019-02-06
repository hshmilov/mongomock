#!/usr/local/bin/python3
import importlib
import sys
import subprocess
import glob
import os


def main():
    try:
        action = sys.argv[1]
        use_case = None
        assert action in ['run', 'ls']
        if action == 'run':
            use_case = sys.argv[2]
    except Exception:
        print(
            f'Usage: \n'
            f'{os.path.basename(sys.argv[0])} ls\n'
            f'{os.path.basename(sys.argv[0])} run [use_case_name]'
        )
        return -1

    if action == 'ls':
        print('Use Cases:')
        for filename in glob.iglob(os.path.join('mockingbird', 'use_cases', '*.py')):
            if '__init__.py' in filename:
                continue
            use_case_name = os.path.basename(filename)[:-3]
            print(f'[*] {use_case_name}')
    elif action == 'run':
        # Import the use case
        use_case_module = importlib.import_module(f'mockingbird.use_cases.{use_case}')
        use_case_main = getattr(use_case_module, 'main')

        print('Reloading use case', flush=True)
        use_case_main()

    return 0


if __name__ == '__main__':
    sys.exit(main())
