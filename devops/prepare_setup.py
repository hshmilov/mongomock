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
    parser.add_argument('--image-tag', type=str, default='', help='Image Tag, will be used as Dockerfile image tag')

    try:
        args, _ = parser.parse_known_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    return args


def main():
    args = setup_args()
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    all_flag = '' if args.dev else '--all'

    # build
    build_cmd = ['./axonius.sh', 'system', 'build', all_flag, '--prod', '--hard', '--yes-hard', '--rebuild-libs']
    if args.image_tag:
        build_cmd.extend(['--image-tag', args.image_tag])

    print(" ".join(build_cmd))


if __name__ == '__main__':
    main()
