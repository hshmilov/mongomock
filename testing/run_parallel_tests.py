import pytest
import glob
import os
import sys
import time

from devops.parallel_runner import ParallelRunner
from services.axonius_service import get_service


class ParallelTestsRunner(ParallelRunner):

    def append_test_pattern(self, pattern, **kwargs):
        for file in sorted(glob.glob(pattern)):
            test_case = os.path.basename(file).split(".")[0]
            command = f"pytest -x -s -v --showlocals --durations=0 --junitxml=reporting/{test_case}.xml {file}"
            self.append_single(test_case, command, **kwargs)


def main():
    # we start axonius system twice during CI test run. One time for 'regular' tests and the second for a parallel run
    axonius = get_service()
    try:

        # taking ownership of process
        axonius.db.take_process_ownership()
        axonius.core.take_process_ownership()
        axonius.aggregator.take_process_ownership()
        axonius.gui.take_process_ownership()

        axonius.start_and_wait()
        runner = ParallelTestsRunner()
        pattern = sys.argv[1]
        print(f"Running in parallel for pattern {pattern}")
        runner.append_test_pattern(pattern)
        return runner.wait_for_all(500, 1)
    finally:
        axonius.stop(should_delete=True)


if __name__ == '__main__':
    sys.exit(main())
