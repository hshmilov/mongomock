#!/usr/bin/env python3

import os


def create_pth_file():
    axon_pth_file_path = '/usr/local/lib/python3.6/dist-packages/axonius.pth'
    if not os.path.exists(os.path.dirname(axon_pth_file_path)):
        axon_pth_file_path = '/usr/local/lib/python3.6/site-packages/axonius.pth'
    current__dir = os.path.dirname(os.path.realpath(__file__))
    cortex_dir = os.path.join(current__dir, '..')
    with open(axon_pth_file_path, 'w') as pth_file:
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'axonius-libs', 'src',
                                                    'libs', 'axonius-py')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'plugins')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'testing')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'adapters')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'deployment')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'devops')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'devops', 'CI', 'builds_website', 'sdk')) + '\n')
        pth_file.write(os.path.abspath(os.path.join(cortex_dir)) + '\n')
    print(axon_pth_file_path)


if __name__ == '__main__':
    create_pth_file()
