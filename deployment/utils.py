import sys
import os


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
        3. the loader (when using ziploader)

        Under the next two states: when the current python __main__ module is run from (a) a zip file, and (b) normally.
    """
    main_module = sys.modules['__main__']
    loader = main_module.__loader__
    if loader is None or loader.__class__.__name__ == 'SourceFileLoader' or \
            (hasattr(loader, '__name__') and loader.__name__ == 'BuiltinImporter'):
        current_file = os.path.abspath(__file__)
        return os.path.abspath(os.path.join(os.path.dirname(current_file), '..')), current_file, None
    assert loader.__class__.__name__ == 'zipimporter'
    archive_path = loader.archive
    assert os.path.isfile(archive_path)
    return None, os.path.abspath(archive_path), loader


def print_state(text):
    reset = '\033[00m'
    light_blue = '\033[94m'
    print(f'{light_blue}{text}{reset}')


CORTEX_PATH, current_file_system_path, zip_loader = get_resources()
CWD = os.path.abspath(os.getcwd())
AXONIUS_DEPLOYMENT_PATH = os.path.join(CWD, 'cortex')
AXONIUS_OLD_ARCHIVE_PATH = os.path.join(CWD, 'old-cortex-archive-{0}.tar.gz')
SOURCES_FOLDER_NAME = 'sources'


def safe_run_bash(args):
    assert args[0].endswith('.sh')
    if sys.platform.startswith('win'):
        bash_path = r'C:\Program Files\Git\git-bash.exe'
        assert os.path.isfile(bash_path)
        name = args[0]
        if name.startswith('./'):
            name = name[2:]
        args = [bash_path, name] + args[1:]
    return args


if CORTEX_PATH is not None:
    try:
        import axonius  # used by the imports below and get_service assumes it is importable
    except (ModuleNotFoundError, ImportError):
        # if not in path...
        sys.path.append(os.path.abspath(os.path.join(CORTEX_PATH, 'axonius-libs', 'src', 'libs', 'axonius-py')))

    try:
        from services.axonius_service import get_service
    except (ModuleNotFoundError, ImportError):
        # if not in path...
        sys.path.append(os.path.abspath(os.path.join(CORTEX_PATH, 'testing')))
        from services.axonius_service import get_service


def get_mongo_client():
    # Import inside so it won't fail on install when venv is not ready yet...
    from configparser import ConfigParser
    from pymongo import MongoClient

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plugins', 'core', 'config.ini')
    config = ConfigParser()
    config.read(config_path)

    db_host = config['core_specific']['db_addr'].replace('mongo:', 'localhost:')
    db_user = config['core_specific']['db_user']
    db_password = config['core_specific']['db_password']
    return MongoClient(db_host, username=db_user, password=db_password)
