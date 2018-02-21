import inspect
import sys

COLOR = {
    'reset': '\033[00m',

    'black': '\033[30m',
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'magenta': '\033[35m',
    'cyan': '\033[36m',
    'light_grey': '\033[37m',

    'dark_grey': '\033[90m',
    'light_red': '\033[91m',
    'light_green': '\033[92m',
    'light_yellow': '\033[93m',
    'light_blue': '\033[94m',
    'light_magenta': '\033[95m',
    'light_cyan': '\033[96m',
    'white': '\033[97m',
}


def debugprint(s, color="green"):
    print(f"{COLOR[color]}{s}{COLOR['reset']}")
    sys.stdout.flush()


def greenprint(s):
    debugprint(s, 'light_green')


def blueprint(s):
    debugprint(s, 'light_blue')


def redprint(s):
    debugprint(s, 'light_red')


def is_debug_attached():
    if '_pydev_bundle' not in sys.modules:
        return False
    test_module = sys.modules['_pydev_bundle']
    return inspect.getfile(test_module).startswith('/opt/.pycharm_helpers/pydev/_pydev_bundle')
