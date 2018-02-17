import os
import sys

try:
    from test_helpers.parallel_runner import ParallelRunner
except (ModuleNotFoundError, ImportError):
    # if not in path...
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'testing'))
    from test_helpers.parallel_runner import ParallelRunner


def safe_run_bash(args):
    assert args[0].endswith('.sh')
    if sys.platform.startswith('win'):
        name = args[0]
        if name.startswith('./'):
            name = name[2:]
        args = [r'C:\Program Files\Git\git-bash.exe', name] + args[1:]
    return args


if __name__ == '__main__':
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    runner = ParallelRunner()

    # first build libs
    runner.append_single('axonius-libs', ['docker', 'build', 'plugins/axonius-libs', '-t', 'axonius/axonius-libs'])
    print("waiting to build axonius-libs")
    assert runner.wait_for_all() == 0

    # venv
    runner.append_single('venv', safe_run_bash(['./create_venv.sh']))
    assert runner.wait_for_all() == 0

    runner.append_single('system', safe_run_bash(['./axonius.sh', 'system', 'build', '--all', '--prod']))
    assert runner.wait_for_all() == 0
