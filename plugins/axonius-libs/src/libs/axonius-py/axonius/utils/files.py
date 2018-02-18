import os


CONFIG_FILE_NAME = 'config.ini'


def get_local_config_file(current_import_file):
    return os.path.abspath(os.path.join(os.path.dirname(current_import_file), CONFIG_FILE_NAME))
