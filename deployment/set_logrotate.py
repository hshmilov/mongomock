import os
import subprocess
import sys


CORTEX_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def main():
    if sys.platform.startswith('win'):
        print('Skipping logrotation on Windows platform')
        return

    ops = []
    # docker logs
    ops.append(write_logrotate('/etc/logrotate.d/docker-container', '/var/lib/docker/containers/*/*.log'))
    # our logs
    ops.append(write_logrotate('/etc/logrotate.d/axonius', os.path.join(CORTEX_PATH, 'logs', '*', '*.docker.log'),
                               True))

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

    if os.getuid() != 0:  # needs elevation
        sys.exit(subprocess.call(['sudo', sys.executable] + sys.argv))

    # Actually update the files
    for op in commit_ops:
        try:
            next(op)
        except StopIteration:
            pass


def write_logrotate(path, path_regex, with_su=False):
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
}""".replace('path_regex', path_regex).replace('with_su', 'su' if with_su else '')
    if os.path.isfile(path) and open(path, 'r').read() == data:
        return
    yield
    open(path, 'w').write(data)


if __name__ == '__main__':
    main()
