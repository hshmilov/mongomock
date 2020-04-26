import argparse
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


def setup_args():
    parser = argparse.ArgumentParser(usage='''
        This script builds the system.
        Using --dev will build only the core of the system and doing so will shorten it's run time.
        Any adapter will be built when explicitly raised if it was not built before.
        ''')
    parser.add_argument('--dev', action='store_true', default=False, help='Dev Mode')

    try:
        args, _ = parser.parse_known_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    return args


def main():
    args = setup_args()
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    runner = ParallelRunner()

    # venv & base image
    runner.append_single('venv', safe_run_bash(['./create_venv.sh']))
    assert runner.wait_for_all() == 0

    all_flag = '' if args.dev else '--all'

    # build
    runner.append_single(
        'system',
        safe_run_bash(['./axonius.sh', 'system', 'build', all_flag, '--prod', '--hard', '--yes-hard', '--rebuild-libs'])
    )
    assert runner.wait_for_all() == 0


if __name__ == '__main__':
    main()
