#!/usr/bin/env python3
import glob
import os
import sys

from test_helpers.parallel_runner import ParallelRunner
from services.axonius_service import get_service


class ParallelTestsRunner(ParallelRunner):
    def append_test_pattern(self, paths, extra_flags, **kwargs):
        files = []
        for path in paths:
            if os.path.isfile(path):
                files.append(path)
            else:
                for file in glob.glob(path):
                    files.append(file)

        for file in sorted(files):
            test_case_name = os.path.basename(file).split('.')[0]
            args = ['python3', '-u', os.path.join(os.path.abspath(os.path.dirname(__file__)), 'run_pytest.py')]
            if extra_flags:
                args.extend(extra_flags)
            args.append(file)
            print(f'Adding {file} to run!')
            self.append_single(test_case_name, args, **kwargs)


def main():
    # we start axonius system twice during CI test run. One time for 'regular' tests and the second for a parallel run
    axonius_system = get_service()
    try:
        axonius_system.take_process_ownership()
        axonius_system.start_and_wait()

        # Set up testing configurations
        axonius_system.core.set_execution_config(True)
        axonius_system.execution.post('update_config')

        # Run all parallel tests
        runner = ParallelTestsRunner()
        extra_flags = []
        paths = []
        for arg in sys.argv[1:]:
            if arg.startswith('-'):
                extra_flags.append(arg)
            else:
                paths.append(arg)

        print(f"Running in parallel, extra flags are {str(extra_flags)}, paths are {str(paths)}")
        runner.append_test_pattern(paths, extra_flags=extra_flags)
        return runner.wait_for_all(120 * 60)
    finally:
        axonius_system.stop(should_delete=True)


if __name__ == '__main__':
    sys.exit(main())
