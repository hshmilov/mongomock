#!/usr/bin/env python3
import subprocess
import shlex
import getpass
import sys


def main():
    decryption_key = getpass.getpass('Please enter the decryption key> ', stream=sys.stdout)
    try:
        subprocess.check_call(shlex.split(f'sudo /home/decrypt/first_install.py {decryption_key}'))
    except Exception as e:
        print(f'Install procedure failed {e}')
    finally:
        print('Decrypt user - end')


if __name__ == '__main__':
    main()
