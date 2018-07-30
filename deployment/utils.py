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
