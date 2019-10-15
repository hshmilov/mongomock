#!/usr/bin/env python3.6
"""
This script pulls & build all the images and creates a single installer for the entire system.
The final installer zip is comprised of:
    + all images built and pulled (that are necessary for the system to run)
    + local source code (filtering out unnecessary files, folders, plugins and adapters)
    + python required packages
"""
import argparse
import imp
import inspect
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import pip
from pip._vendor.packaging import markers as pip_markers

import lists
from devops.axonius_system import get_metadata
from services.axonius_service import get_service
from utils import (CORTEX_PATH, SOURCES_FOLDER_NAME, AutoOutputFlush,
                   print_state)

if pip.__version__.startswith('9.'):
    import pip.pep425tags as pip_pep425tags
    import pip.utils.glibc as pip_glibc
    from pip import main as pip_main
else:
    import pip._internal.pep425tags as pip_pep425tags
    import pip._internal.utils.glibc as pip_glibc
    import pip._internal.main
    from pip._internal.main import main as pip_main


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--out', type=str, default='axonius_{version}.py')
    parser.add_argument('--version', type=str, default='')
    parser.add_argument('--override', action='store_true', default=False, help='Override output file if already exists')
    parser.add_argument('--pull', action='store_true', default=False, help='Pull base image before rebuild')
    parser.add_argument('--rebuild', action='store_true', default=False, help='Rebuild images')
    parser.add_argument('--winpip', action='store_true', default=False,
                        help='Collect packages *also* for offline windows deployment')
    parser.add_argument('--exclude', metavar='N', type=str, nargs='*', help='Adapters and Services to exclude',
                        default=[])

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    output_path = os.path.abspath(args.out.format(version=args.version))
    if os.path.exists(output_path):
        if not os.path.isfile(output_path):
            raise Exception('Output path cannot point to a directory')
        if not args.override:
            raise Exception('Output path already exists, pass --override to override the file')

    create_package(output_path, args.version, args.pull, args.rebuild, args.exclude, args.winpip)


def create_package(output_path, version='', pull=False, rebuild=False, exclude=None, prod=True, winpip=False):
    """
    The file created (axonius_install{version}.py) is a zip file with the following structure:
    axonius_install{version}.py (zip file):
        sources/
            #cortex sources dir without the filtered content and packages
            ...
            deployment/
                packages/ #python pip packages
        images.tar # docker images collection
        __main__.py
    """
    start = time.time()
    main_template = f"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '{SOURCES_FOLDER_NAME}', 'deployment'))

from utils import AutoOutputFlush
from install import main

print('Axonius package install')
print('Version: {version}')

with AutoOutputFlush():
    main()
"""
    # main_template = 'from IPython import embed\nembed()\n'  # helper template for debugging
    metadata = get_metadata(version=version)
    download_artifacts()
    download_packages(winpip)
    images_tar = get_images_tar(pull, rebuild, exclude, prod)
    try:
        with open(output_path, 'wb') as output_file:
            output_file.write(b'#!/usr/bin/env python3.6\n')
            with zipfile.ZipFile(output_file, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr('__main__.py', main_template.encode('utf-8'))
                zip_file.writestr(f'{SOURCES_FOLDER_NAME}/shared_readonly_files/__build_metadata',
                                  metadata.encode('utf-8'))

                # placeholder for logs dir
                zip_file.writestr(f'{SOURCES_FOLDER_NAME}/logs/nonce', ''.encode('utf-8'))

                add_source_folder(zip_file, os.path.basename(output_path), exclude)
                zip_file.write(images_tar, 'images.tar')
                print_state('Closing zip file')
    finally:
        os.remove(images_tar)
    print_state(f'Done, took {int(time.time() - start)} seconds - saved to {output_path}')


def get_images_tar(pull=False, rebuild=False, exclude=None, prod=True):
    images_tar = tempfile.mktemp(prefix='axonius_images_')
    images = build_images(pull, rebuild, exclude, prod)
    print_state(f'Compiling {len(images)} images')
    print('  ' + '\n  '.join(images))
    print_state('  Saving images to temp file')
    print(f'    {images_tar}')
    try:
        proc = subprocess.Popen(['docker', 'save', '-o', images_tar] + images, stdout=subprocess.PIPE)
        ret_code = proc.wait()
        if ret_code != 0:
            print(f'Docker save images return code: {ret_code}')
            raise Exception('Invalid return code from docker save command')
        return images_tar
    except Exception:
        os.remove(images_tar)
        raise


def build_images(pull=False, rebuild=False, exclude=None, prod=True):
    axonius_system = get_service()
    axonius_system.take_process_ownership()
    images = []
    base_image = 'axonius/axonius-base-image'
    if not pull:
        base_image_exists = base_image in subprocess.check_output(['docker', 'images', base_image]).decode('utf-8')
        if not base_image_exists:
            pull = True
    if pull:
        rebuild = True
    images.append(axonius_system.pull_base_image(pull, show_print=False))
    images.append(axonius_system.pull_tunnler(pull, show_print=False))
    images.append(axonius_system.pull_curl_image(pull, show_print=False))
    images.extend(axonius_system.pull_weave_images(pull, show_print=False))
    print_state(f'Building all images')
    images.append(axonius_system.build_libs(rebuild, show_print=False))
    services = [name for name, variable in axonius_system.get_all_plugins()]
    adapters = [name for name, variable in axonius_system.get_all_adapters()]
    if exclude:
        for name in exclude:
            if name not in services and name not in adapters:
                raise ValueError(f'Excluded name {name} not found')
        services = [name for name in services if name not in exclude]
        adapters = [name for name in adapters if name not in exclude]
    images.extend(axonius_system.build(True, adapters, services, 'prod' if prod else '', rebuild))
    images.sort()
    return images


def add_source_folder(zip_file: zipfile.ZipFile, output_file_name: str, exclude: list = None):
    """ add source folder CORTEX_PATH to zip_file under /SOURCES_FOLDER_NAME;
        first iterate over all files and sub-folders and prepare a list of white-listed files (variable files)
        then, call write_files to commit those files to zip_file.
    """
    install_out_regex = re.compile(output_file_name)
    header = SOURCES_FOLDER_NAME
    files = []
    exclude_files = []
    exclude_folders = []
    if exclude:
        axonius_system = get_service()
        services = dict(axonius_system.get_all_plugins())
        adapters = dict(axonius_system.get_all_adapters())
        for exclude_item in exclude:
            if exclude_item in services:
                service_class = services[exclude_item]
            elif exclude_item in adapters:
                service_class = adapters[exclude_item]
            else:
                continue  # should not happen...
            service = service_class()
            folder_relative_path = os.path.relpath(service.service_dir, CORTEX_PATH).replace('\\', '/')
            if folder_relative_path.endswith('/'):
                folder_relative_path = folder_relative_path[:-1]
            exclude_folders.append(folder_relative_path)
            exclude_files.append(os.path.relpath(inspect.getfile(service_class), CORTEX_PATH).replace('\\', '/'))

    def filter_folder(source_path):
        if source_path in exclude_folders:
            return False
        if os.path.basename(source_path) in lists.FILENAMES_EXCLUDE_GLOBAL:
            return False
        if source_path in lists.DIRS_EXCLUDE_GLOBAL:
            return False
        if (Path(CORTEX_PATH) / Path(source_path) / lists.SKIP_DEPLOYMENT_MARKER).is_file():
            return False
        return True

    def filter_file(source_path):
        if source_path in exclude_files:
            return False
        if source_path.endswith('.bat') or os.path.basename(source_path).startswith('.git'):
            return False
        if source_path in lists.FILENAMES_EXCLUDE_GLOBAL:
            return False
        if install_out_regex.match(source_path):
            return False
        return True

    def add_folder(source_path, zip_rel_path):
        if not filter_folder(source_path.replace('\\', '/')):
            return
        folder_path = os.path.join(CORTEX_PATH, source_path)
        for item in os.listdir(folder_path):
            path = os.path.join(folder_path, item)
            if os.path.isdir(path):
                add_folder(os.path.join(source_path, item), zip_rel_path + '/' + item)
            elif os.path.isfile(path):
                add_file(os.path.join(source_path, item), zip_rel_path + '/' + item)

    def add_file(source_path, zip_rel_path):
        if not filter_file(source_path.replace('\\', '/')):
            return
        path = os.path.join(CORTEX_PATH, source_path)
        files.append((zip_rel_path, path))

    def write_files():
        count_max_size = len(str(len(files))) + 2
        index = 0
        for zip_rel_path, path in files:
            print(f'{index}.'.ljust(count_max_size) + zip_rel_path[len(header) + 1:])
            index += 1
            zip_file.writestr(zip_rel_path, open(path, 'rb').read())

    print_state(f'Collecting sources')
    add_folder('', SOURCES_FOLDER_NAME)
    print(f'  Collected {len(files)} source files')
    print_state(f'Compiling sources')
    write_files()


def download_artifacts():
    """
    Simply calls the download artifacts script to download things from the internet before we create the installer.
    :return:
    """
    subprocess.check_output(os.path.join(CORTEX_PATH, "download_artifacts.sh"))


def download_packages(winpip=False):
    """ Download packages for offline installation on linux,
        pass winpip=True to collect offline installations for windows as well """
    print_state('Downloading requirements')
    requirements = os.path.join(CORTEX_PATH, 'requirements.txt')
    packages = os.path.join(CORTEX_PATH, 'deployment', 'packages')
    if not os.path.isdir(packages):
        os.makedirs(packages)
    args = f'download -r {requirements} -d {packages} --no-cache'.split(' ')

    # pip workaround: override current OS settings with the OVA's: https://github.com/pypa/pip/issues/4289

    if winpip:
        print_state('  Windows requirements')
        # Download support for offline install also on windows
        pip_pep425tags.get_platform = lambda: 'win32'
        pip_markers.default_environment = lambda: {
            'implementation_name': 'cpython',
            'implementation_version': '3.6.3',
            'os_name': 'nt',
            'platform_machine': 'AMD64',
            'platform_python_implementation': 'CPython',
            'platform_release': '10',
            'platform_system': 'Windows',
            'platform_version': '10.0.17134',
            'python_full_version': '3.6.3',
            'python_version': '3.6',
            'sys_platform': 'win32'
        }
        assert pip_main(args) == 0
        print_state('  Linux requirements')

    pip_pep425tags.get_platform = lambda: 'linux_x86_64'
    pip_markers.default_environment = lambda: {
        'implementation_name': 'cpython',
        'implementation_version': '3.6.3',
        'os_name': 'posix',
        'platform_machine': 'x86_64',
        'platform_release': '4.4.0-62-generic',
        'platform_system': 'Linux',
        'platform_version': '#83-Ubuntu SMP Wed Jan 18 14:10:15 UTC 2017',
        'python_full_version': '3.6.3',
        'platform_python_implementation': 'CPython',
        'python_version': '3.6',
        'sys_platform': 'linux'
    }
    pip_pep425tags.is_manylinux1_compatible = lambda: True
    pip_pep425tags._is_running_32bit = lambda: False
    imp.get_suffixes = lambda: [('.cpython-36m-x86_64-linux-gnu.so', 'rb', 3),
                                ('.abi3.so', 'rb', 3),
                                ('.so', 'rb', 3),
                                ('.py', 'r', 1),
                                ('.pyc', 'rb', 2)]
    pip_glibc.glibc_version_string = lambda: '2.23'
    assert pip_main(args) == 0


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
