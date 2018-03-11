import os
import tempfile

CONFIG_FILE_NAME = 'config.ini'


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
