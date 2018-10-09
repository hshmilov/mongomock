#!/usr/bin/env python3
import glob
import os
import sys

from test_helpers.parallel_runner import ParallelRunner
from services.axonius_service import get_service


class ParallelTestsRunner(ParallelRunner):
    def append_test_pattern(self, pattern, extra_flags, **kwargs):
        for file in sorted(glob.glob(pattern)):
            test_case = os.path.basename(file).split(".")[0]
            args = f"pytest -s -vv --showlocals --durations=0"
            if extra_flags:
                args = f"{args} {extra_flags}"
            args = f"{args} --junitxml=reporting/{test_case}.xml {file}".split(' ')
            self.append_single(test_case, args, **kwargs)


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
        pattern = sys.argv[-1]
        extra_flags = ' '.join(sys.argv[1:-1])
        print(f"Running in parallel for pattern {pattern}")
        runner.append_test_pattern(pattern, extra_flags=extra_flags)
        return runner.wait_for_all(120 * 60)
    finally:
        axonius_system.stop(should_delete=True)


if __name__ == '__main__':
    sys.exit(main())
