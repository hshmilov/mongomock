import os
import sys

HOSTS_FILE_URL = '/etc/hosts'
HOSTS_FILE_URL_FOR_WINDOWS = 'C:\\Windows\\System32\\drivers\\etc\\hosts'
TEMP_HOSTS_FILE_URL = '/tmp/etc_hosts.tmp'


class HostsFileModifier:
    @staticmethod
    def add_url_if_not_exist(ip, url):
        if os.name == 'nt':
            file_path = HOSTS_FILE_URL_FOR_WINDOWS
        else:
            file_path = HOSTS_FILE_URL

        with open(file_path, 'r') as hosts_file:
            lines = hosts_file.readlines()
        for line in lines:
            if url in line:
                return

        if os.name == 'nt':
            with open(file_path, 'a') as hosts_file:
                hosts_file.writelines([f'\n{ip} {url}', f'\n{ip} www.{url}'])
        else:
            with open(file_path, 'r') as f:
                s = f'{f.read()} \n{ip}\t{url}\n{ip}\twww.{url}\n'
            with open(TEMP_HOSTS_FILE_URL, 'w') as outf:
                outf.write(s)

            os.system(f'sudo mv {TEMP_HOSTS_FILE_URL} {file_path}')


def main():
    ip, url = sys.argv[1], sys.argv[2]
    print(f'setting {ip} {url} pair')
    HostsFileModifier.add_url_if_not_exist(ip, url)
    print(f'set {ip} {url} pair')
    return 0


if __name__ == '__main__':
    sys.exit(main())
