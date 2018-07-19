#!/usr/bin/env python3

import os
import sys


def create_pth_file():
    current__dir = os.path.dirname(os.path.realpath(__file__))
    cortex_dir = os.path.join(current__dir, '..')
    axon_pth_file_path = os.path.join(cortex_dir, 'venv', 'lib')
    if not sys.platform.startswith('win'):
        axon_pth_file_path = os.path.join(axon_pth_file_path, 'python3.6')
    axon_pth_file_path = os.path.join(axon_pth_file_path, 'site-packages', 'axonius.pth')
    with open(axon_pth_file_path, 'w') as pth_file:
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'axonius-libs', 'src',
                                                    'libs', 'axonius-py')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'plugins')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'testing')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'adapters')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'deployment')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'devops')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir)) + '\n')


if __name__ == '__main__':
    create_pth_file()
