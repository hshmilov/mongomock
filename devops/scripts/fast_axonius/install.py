#!/usr/bin/env python3

import os
import shutil
import sys


def main():
    current__dir = os.path.dirname(os.path.realpath(__file__))

    shutil.copyfile(os.path.abspath(os.path.join(current__dir, 'axonius.py')),
                    os.path.abspath(os.path.join(os.path.expanduser("~"), '.ipython', 'profile_default', 'startup',
                                                 'axonius.py')))


if __name__ == '__main__':
    main()
