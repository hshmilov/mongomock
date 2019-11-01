#!/usr/bin/env python3
import argparse
import random
import shlex
import string
from pathlib import Path
from subprocess import run, STDOUT

from devops.scripts.automate_dev.release_checklist import get_env


def new_passw(length=12):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def copy_release_to_password_protected(env):
    print(f'Copying release to password protected link (https://axonius-releases.axonius.com/axonius_release.ova)')
    cmd = 'aws s3 cp ' \
          's3://axonius-releases/latest_release/axonius_release.ova ' \
          's3://release-links/axonius_release.ova ' \
          '--region us-east-2'
    run(shlex.split(cmd), env=env, check=True, shell=True, stderr=STDOUT)


def regenereate_password(env):
    new_pass = new_passw()
    print(f'You new password is {new_pass}')
    pass_file = Path('password')
    pass_file.write_text(new_pass)
    cmd = f'aws s3 cp {pass_file} s3://deploy-pass/password --region us-east-2'
    run(shlex.split(cmd), env=env, check=True, shell=True, stderr=STDOUT)
    pass_file.unlink()


def remove_public_link(env):
    print(f'Deleting old release link')
    cmd = 'aws s3 rm s3://axonius-releases/latest_release/axonius_release.ova --region us-east-2'
    run(shlex.split(cmd), env=env, check=True, shell=True, stderr=STDOUT)


def main():
    parser = argparse.ArgumentParser(description='Release checklist')

    parser.add_argument('--aws-key', action='store', help='AWS key', required=True)
    parser.add_argument('--aws-secret', action='store', help='AWS secret', required=True)
    parser.add_argument('--gen-new-pass', action='store', help='Should I generate and set a new password?',
                        required=False, default=True)
    parser.add_argument('--delete-unprotected', action='store', help='Should I delete the public link?',
                        required=False, default=False)

    args = parser.parse_args()

    aws_key = args.aws_key
    aws_secret = args.aws_secret
    gen_new_pass = args.gen_new_pass
    delete_unprotected = args.delete_unprotected

    aws_env = get_env(aws_key, aws_secret)

    copy_release_to_password_protected(aws_env)

    if gen_new_pass:
        regenereate_password(aws_env)

    if delete_unprotected:
        remove_public_link(aws_env)


if __name__ == '__main__':
    main()
