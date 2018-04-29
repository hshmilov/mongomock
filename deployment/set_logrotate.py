import os
import subprocess
import sys


CORTEX_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def main():
    if sys.platform.startswith('win'):
        print('Skipping logrotation on Windows platform')
        return
    if os.getuid() != 0:  # needs elevation
        sys.exit(subprocess.call(['sudo', sys.executable] + sys.argv))
    # docker logs
    write_logrotate('/etc/logrotate.d/docker-container', '/var/lib/docker/containers/*/*.log')
    # our logs
    write_logrotate('/etc/logrotate.d/axonius', os.path.join(CORTEX_PATH, 'logs', '*', '*.docker.log'), True)


def write_logrotate(path, path_regex, with_su=False):
    # see https://sandro-keil.de/blog/2015/03/11/logrotate-for-docker-container/
    open(path, 'w').write("""path_regex {
  rotate 7
  daily
  compress
  size=1M
  missingok
  delaycompress
  copytruncate
  with_su
}""".replace('path_regex', path_regex).replace('with_su', 'su' if with_su else ''))


if __name__ == '__main__':
    main()
