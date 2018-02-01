"""
Some debugging tricks.
blueprint, redprint etc print colorful strings to the console.
"""
import sys

COLOR = {
    'blue': '\033[94m',
    'default': '\033[99m',
    'grey': '\033[90m',
    'yellow': '\033[93m',
    'black': '\033[90m',
    'cyan': '\033[96m',
    'green': '\033[92m',
    'magenta': '\033[95m',
    'white': '\033[97m',
    'red': '\033[91m'
}

# Prints strings in a colorful way to the console.


def debugprint(s, color="green"):
    print(f"{COLOR[color]}==========> {s}")
    sys.stdout.flush()


def greenprint(s):
    debugprint(s, 'green')


def blueprint(s):
    debugprint(s, 'blue')


def redprint(s):
    debugprint(s, 'red')
