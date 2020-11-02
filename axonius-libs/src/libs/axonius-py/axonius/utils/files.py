import os
import tempfile
import time

CONFIG_FILE_NAME = 'config.ini'
DEFAULT_SERVICE_DIR = '/home/ubuntu/cortex'
UPLOADED_FILES_DIR = '/home/axonius/uploaded_files'
SHARED_READONLY_DIR = '/home/axonius/shared_readonly_files'
UPLOADED_HOST_FILES_DIR = os.path.join(DEFAULT_SERVICE_DIR, 'uploaded_files')


def get_local_config_file(current_import_file):
    return os.path.abspath(os.path.join(os.path.dirname(current_import_file), CONFIG_FILE_NAME))


def create_temp_file(data: bytes):
    """
    Creates a temporary file with some data, that can be read from
    :param data: data to write
    :return:
    """
    file = tempfile.NamedTemporaryFile()
    file.write(data)
    file.flush()
    return file


def get_random_uploaded_path_name(filename_suffix):
    """
    returns a file path with a random_prefix filename for an uploaded file.
    Note that the path returned is a local path that is accessible from all containers,
    since its mapped.
    :param filename_suffix: e.g. some_binary. the filename will be stored as timestamp_[filename_suffix]
    :return: (file_handle, file_path)
    """

    # an extremely rare race-condition. only if a user requests to upload more than one file on a very specific
    # milli (or nano, or more) second. so the race condition is nearly impossible.
    filename = f'{time.time()}_{filename_suffix}'
    full_path = os.path.join(UPLOADED_FILES_DIR, filename)
    return full_path


def get_all_uploaded_files():
    return [os.path.join(UPLOADED_FILES_DIR, file_path) for file_path in os.listdir(UPLOADED_FILES_DIR)
            if os.path.isfile(os.path.join(UPLOADED_FILES_DIR, file_path))]
