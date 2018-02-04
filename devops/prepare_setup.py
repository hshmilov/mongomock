import os
import sys

try:
    from test_helpers.parallel_runner import ParallelRunner
except (ModuleNotFoundError, ImportError):
    # if not in path...
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'testing'))
    from test_helpers.parallel_runner import ParallelRunner


if __name__ == '__main__':
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    runner = ParallelRunner()

    # first build libs
    runner.append_single('axonius-libs', ['docker', 'build', 'plugins/axonius-libs', '-t', 'axonius/axonius-libs'])
    print("waiting to build axonius-libs")
    assert runner.wait_for_all() == 0

    # venv
    runner.append_single('venv', ['./create_venv.sh'])
    assert runner.wait_for_all() == 0

    runner.append_single('system', ['./axonius.sh', 'system', 'build', '--all'])
    assert runner.wait_for_all() == 0
