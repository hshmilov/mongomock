import sys

import pymongo


def main():
    devices_db = pymongo.MongoClient('localhost', port=28017).mock_db['devices']
    try:
        _, txt_file = sys.argv  # pylint: disable=unbalanced-tuple-unpacking
    except Exception:
        print(f'Usage: {sys.argv[0]} <txt_file> - csv_file is a file with ip addresses exported by axonius')
        return -1

    ips = set()
    with open(txt_file, 'rt') as f:
        for line in f.readlines():
            for ip in line.split(','):
                ips.add(ip.strip())
    for ip in ips:
        res = devices_db.delete_many({'data.network_interfaces.ips': ip})
        print(f'Done with ip {ip}: {str(res)}')

    print(f'Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
