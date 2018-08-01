import argparse
import os
import sys


def set_logrotate(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--cortex-path', type=str, help='Cortex path', required=True)

    try:
        args = parser.parse_args(args)
    except AttributeError:
        print(parser.usage())
        return

    cortex_path = args.cortex_path

    ops = list()
    # docker logs
    ops.append(write_logrotate('/etc/logrotate.d/docker-container', '/var/lib/docker/containers/*/*.log'))
    # our logs
    ops.append(write_logrotate('/etc/logrotate.d/axonius', os.path.join(cortex_path, 'logs', '*', '*.log')))

    # Check if we need to update the files, if not, skip elevation (prompt for root password...)
    commit_ops = []
    for op in ops:
        i = iter(op)
        try:
            next(op)
        except StopIteration:
            pass
        else:
            commit_ops.append(i)
    if len(commit_ops) == 0:
        return

    # Actually update the files
    for op in commit_ops:
        try:
            next(op)
        except StopIteration:
            pass


def write_logrotate(path, path_regex, as_ubuntu=False):
    # see https://sandro-keil.de/blog/2015/03/11/logrotate-for-docker-container/
    data = """path_regex {
  rotate 7
  daily
  compress
  size=1M
  missingok
  delaycompress
  copytruncate
  with_su
}""".replace('path_regex', path_regex).replace('with_su', 'su ubuntu ubuntu' if as_ubuntu else '')
    if os.path.isfile(path) and open(path, 'r').read() == data:
        return
    yield
    open(path, 'w').write(data)


if __name__ == '__main__':
    set_logrotate(sys.argv[1:])
