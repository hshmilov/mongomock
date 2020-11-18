import shutil
import sys
import os
import subprocess
from pathlib import Path

MIN_GB_FOR_INSTALLATION = 20


# note: DO NOT IMPORT ANY EXTERNAL PACKAGE (axonius included) HERE. THIS FILE RUNS BEFORE VENV IS SET!

class AutoOutputFlush(object):
    def __init__(self):
        self._stdout_write = sys.stdout.write
        self._stderr_write = sys.stderr.write

    def write_stdout(self, text):
        self._stdout_write(text)
        sys.stdout.flush()

    def write_stderr(self, text):
        self._stderr_write(text)
        sys.stderr.flush()

    def __enter__(self):
        sys.stdout.write = self.write_stdout
        sys.stderr.write = self.write_stderr

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.write = self._stdout_write
        sys.stderr.write = self._stderr_write


def get_resources():
    """ a special function that gets:
        1. CORTEX_PATH (when run from zip, assume there isn't a clone of the source code)
        2. original path of the executable
    """
    current_file = os.path.abspath(__file__)
    return os.path.abspath(os.path.join(os.path.dirname(current_file), '..')), current_file


def print_state(text):
    reset = '\033[00m'
    light_blue = '\033[94m'
    print(f'{light_blue}{text}{reset}')


def run_cmd(args):
    subprocess.call(args)


def chown_folder(path: str, sudo: bool = False):
    """
    Changing ownership of a dir and sub dirs recursively.
    :param path: The path to change ownership to.
    :param sudo: Should use sudo or not.
    """
    cmd = ''
    if sudo:
        cmd = 'sudo '
    cmd += f'chown -R ubuntu:ubuntu {path}'
    run_cmd(cmd.split())


def show_weave_info():
    try:
        weave_status_connections = subprocess.check_output(['weave', 'status', 'connections']).decode('utf-8').strip()
        if weave_status_connections:
            print_state('Note! this system is part of an active weave cluster.')
    except Exception as e:
        print_state(f'Could not get status of "weave status connections". This could be normal. moving on: {str(e)}')


def verify_storage_requirements():
    try:
        current_dir_free_bytes_left = shutil.disk_usage(CWD).free
        docker_info = subprocess.check_output(['docker', 'info']).decode('utf-8')
        for line in docker_info.splitlines():
            if 'docker root dir' in line.lower():
                root_docker_dir = line.split(':')[1].strip()
                break
        else:
            raise ValueError(f'Can not find "Root Docker Dir" in docker info')

        current_docker_dir_free_bytes_left = shutil.disk_usage(root_docker_dir).free

        print(f'Storage left in current directory: {round(current_dir_free_bytes_left / (1024 ** 3), 2)}gb')
        print(f'Storage left in docker mount: {round(current_docker_dir_free_bytes_left / (1024 ** 3), 2)}gb')

        overall_free_bytes_left = min(current_dir_free_bytes_left, current_docker_dir_free_bytes_left)
        if round(overall_free_bytes_left / (1024 ** 3), 2) < MIN_GB_FOR_INSTALLATION:
            print(f'Not proceeding - must have at least {MIN_GB_FOR_INSTALLATION}gb left')
            sys.exit(-1)
    except Exception as e:
        print(f'Warning - could not get storage information: {str(e)}, continuing')


CORTEX_PATH, current_file_system_path = get_resources()
CWD = os.path.abspath(os.getenv('ORIGINAL_PWD', os.getcwd()))
# Check if inside docker or not
if Path('/.dockerenv').exists():
    AXONIUS_DEPLOYMENT_PATH = CWD
else:
    AXONIUS_DEPLOYMENT_PATH = os.path.join(CWD, 'cortex')
DEPLOYMENT_FOLDER_PATH = os.path.join(AXONIUS_DEPLOYMENT_PATH, 'deployment')
RESOURCES_PATH = os.path.join(DEPLOYMENT_FOLDER_PATH, 'resources')
AXONIUS_OLD_ARCHIVE_PATH = os.path.join(CWD, 'old-cortex-archive-{0}.tar.gz')
SOURCES_FOLDER_NAME = 'sources'
INSTALLER_TEMP_DIR = 'tmp_install_dir'
VENV_WRAPPER = os.path.join(DEPLOYMENT_FOLDER_PATH, 'venv_wrapper.sh')
