import argparse
import sys

import requests

from builds import Builds


def get_export(export_name=None, builds_instance=None):
    if builds_instance is None:
        builds_instance = Builds()

    if export_name:
        return builds_instance.get_export_by_name(export_name)

    return builds_instance.get_latest_daily_export()


def parse_arguments():
    parser = argparse.ArgumentParser(description='Download installer of either a specific version or latest nightly.')

    parser.add_argument('-o', '--out', type=str, help='The full path to save the installer to', required=True)
    parser.add_argument('-v', '--version', type=str, help='Name of a specific version to download', default='')
    parser.add_argument('-q', '--quiet', type=str, help='Should not print the downloaded version name', default='')

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    return args


def main():
    args = parse_arguments()
    export_name = args.version
    installer_path = args.out
    export = get_export(export_name)

    if not args.quiet:
        print(f'Downloading version: {export["version"]}')

    myfile = requests.get(export['installer_download_link'])

    open(installer_path, 'wb').write(myfile.content)


if __name__ == '__main__':
    main()
