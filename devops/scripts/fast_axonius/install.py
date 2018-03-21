import os
import shutil
import sys


def main():
    current__dir = os.path.dirname(os.path.realpath(__file__))
    cortex_dir = os.path.join(current__dir, '..', '..', '..')
    axon_pth_file_path = os.path.join(cortex_dir, 'venv', 'lib')
    if not sys.platform.startswith('win'):
        axon_pth_file_path = os.path.join(axon_pth_file_path, 'python3.6')
    axon_pth_file_path = os.path.join(axon_pth_file_path, 'site-packages', 'axonius.pth')
    if not os.path.isfile(axon_pth_file_path):
        with open(axon_pth_file_path, 'w') as pth_file:
            pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'plugins', 'axonius-libs', 'src',
                                                        'libs', 'axonius-py')) + '\n')
            pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'plugins')) + '\n')
            pth_file.write(os.path.abspath(os.path.join(cortex_dir, 'testing')) + '\n')
            pth_file.write(os.path.abspath(os.path.join(cortex_dir)) + '\n')
    shutil.copyfile(os.path.abspath(os.path.join(current__dir, 'axonius.py')),
                    os.path.abspath(os.path.join(os.path.expanduser("~"), '.ipython', 'profile_default', 'startup',
                                                 'axonius.py')))


if __name__ == '__main__':
    main()
