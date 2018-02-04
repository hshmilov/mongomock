import glob
import os
import sys

from test_helpers.parallel_runner import ParallelRunner
from services.axonius_service import get_service


class ParallelTestsRunner(ParallelRunner):

    def append_test_pattern(self, pattern, **kwargs):
        for file in sorted(glob.glob(pattern)):
            test_case = os.path.basename(file).split(".")[0]
            args = f"pytest -x -s -v --showlocals --durations=0 --junitxml=reporting/{test_case}.xml {file}".split(' ')
            self.append_single(test_case, args, **kwargs)


def main():
    # we start axonius system twice during CI test run. One time for 'regular' tests and the second for a parallel run
    axonius_system = get_service()
    try:
        axonius_system.take_process_ownership()
        axonius_system.start_and_wait()
        runner = ParallelTestsRunner()
        pattern = sys.argv[1]
        print(f"Running in parallel for pattern {pattern}")
        runner.append_test_pattern(pattern)
        return runner.wait_for_all(10 * 60)
    finally:
        axonius_system.stop(should_delete=True)


if __name__ == '__main__':
    sys.exit(main())
