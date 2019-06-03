#!/usr/bin/env python3
import os
import sys
import argparse
import shlex
from subprocess import STDOUT, run

from builds import Builds


AWS_KEY_VAR = 'AWS_ACCESS_KEY_ID'
AWS_SECRET_VAR = 'AWS_SECRET_ACCESS_KEY'
REGION = 'us-east-2'


def flush():
    sys.stdout.flush()
    sys.stderr.flush()


def log(message):
    print(message)
    flush()


def get_env(aws_key, aws_secret):
    env = os.environ.copy()
    env[AWS_KEY_VAR] = aws_key
    env[AWS_SECRET_VAR] = aws_secret
    return env


def upload_to_tests_folder(aws_key, aws_secret, version_name, **_):
    env = get_env(aws_key, aws_secret)

    command = f'aws s3 cp s3://axonius-releases/{version_name}/axonius_{version_name}.py' \
              ' s3://axonius-releases/latest/axonius_latest.py' \
              ' --acl public-read' \
              f' --region {REGION}'

    log('Copying upgrader to automatic tests folder')
    run(shlex.split(command), env=env, shell=True, check=True, stderr=STDOUT)


def upload_to_production(aws_key, aws_secret, version_name, **_):
    upgrader_command = f'aws s3 cp s3://axonius-releases/{version_name}/axonius_{version_name}.py' \
                       ' s3://axonius-releases/latest_release/axonius_upgrader.py' \
                       ' --acl public-read' \
                       f' --region {REGION}'

    ova_command = f'aws s3 cp s3://axonius-releases/{version_name}/{version_name}/{version_name}_export.ova' \
                  ' s3://axonius-releases/latest_release/axonius_release.ova' \
                  ' --acl public-read' \
                  f' --region {REGION}'

    env = get_env(aws_key, aws_secret)

    log('Copying upgrader to production')
    run(shlex.split(upgrader_command), env=env, shell=True, check=True, stderr=STDOUT)

    log('Copying OVA to production')
    run(shlex.split(ova_command), env=env, shell=True, check=True, stderr=STDOUT)

    log('Files copied to production')


def create_tag(version_name, commit_hash, **_):
    tag_command = f'git tag {version_name} {commit_hash}'
    push_command = f'git push upstream {version_name}'

    log('Creating tag')
    run(shlex.split(tag_command), shell=True, check=True, stderr=STDOUT)
    run(shlex.split(push_command), shell=True, check=True, stderr=STDOUT)


def print_epilog(version_name, ami_id, commit_hash, **_):
    log(f'commit_hash: {commit_hash}')
    log(f'ami-id: {ami_id}')
    log(
        f'OVA link: https://axonius-releases.s3-accelerate.amazonaws.com/{version_name}/{version_name}/{version_name}_export.ova')
    log(f'Upgrader link: https://axonius-releases.s3-accelerate.amazonaws.com/{version_name}/axonius_{version_name}.py')
    log('Release checklist is finished successfully!')


def main():
    parser = argparse.ArgumentParser(description='Release checklist')

    parser.add_argument('--aws-key', action='store',
                        help='AWS key', required=True)
    parser.add_argument('--aws-secret', action='store',
                        help='AWS secret', required=True)
    parser.add_argument('--version-name', action='store',
                        help='Version name', required=True)

    args = parser.parse_args()

    builds_instance = Builds()
    export = builds_instance.get_export_by_name(args.version_name)
    commit_hash = export['git_hash']
    ami_id = export['ami_id']

    arguments = dict(aws_key=args.aws_key,
                     aws_secret=args.aws_secret,
                     version_name=args.version_name,
                     commit_hash=commit_hash,
                     ami_id=ami_id)

    create_tag(**arguments)

    upload_to_tests_folder(**arguments)

    upload_to_production(**arguments)

    print_epilog(**arguments)


if __name__ == '__main__':
    main()
