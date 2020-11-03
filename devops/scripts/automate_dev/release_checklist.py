#!/usr/bin/env python3
import argparse
import os
import shlex
import sys
from pathlib import Path
from subprocess import STDOUT, run

from CI.exports.version_passwords import VersionPasswords
from scripts.automate_dev.share_ami import AmiShare
from builds import Builds

AXONIUS_SAAS_ACCOUNT_ID = '604119231150'
AWS_KEY_VAR = 'AWS_ACCESS_KEY_ID'
AWS_SECRET_VAR = 'AWS_SECRET_ACCESS_KEY'
REGION = 'us-east-2'
SAAS_REGIONS = ['us-east-1', 'ca-central-1']


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


def run_on_subprocess(command, *args, **kwargs):
    if sys.platform.startswith('win'):
        command = shlex.split(command)

    return run(command, *args, **kwargs)


def upload_to_cf_protected_bucket(aws_key, aws_secret, version_name, **_):
    env = get_env(aws_key, aws_secret)
    cloudflare_protected_bucket = 'upgrader-links.axonius.com'

    # this location is used by se-ci to fetch the 'latest-release' version
    command = f'aws s3 cp s3://axonius-releases/{version_name}/axonius_{version_name}.py' \
              f' s3://{cloudflare_protected_bucket}/latest/axonius_latest.py' \
              f' --region {REGION}'

    log('Copying upgrader to cloudflare protected version location')
    run_on_subprocess(command, env=env, shell=True, check=True, stderr=STDOUT)

    # chef will use this location to pull upgrades from
    command = f'aws s3 cp s3://axonius-releases/{version_name}/axonius_{version_name}.py' \
              f' s3://{cloudflare_protected_bucket}/{version_name}/axonius_{version_name}.py' \
              f' --region {REGION}'

    log('Copying upgrader to cloudflare protected bucket')
    run_on_subprocess(command, env=env, shell=True, check=True, stderr=STDOUT)

    cloudflare_protected_url = f'https://{cloudflare_protected_bucket}/{version_name}/axonius_{version_name}.py'
    log(f'Upgrade link to place in chef: {cloudflare_protected_url}')


def upload_to_production(aws_key, aws_secret, version_name, ami_id, **_):
    upgrader_command = f'aws s3 cp s3://axonius-releases/{version_name}/axonius_{version_name}.py' \
                       ' s3://axonius-releases/latest_release/axonius_upgrader.py' \
                       f' --region {REGION}'

    ova_command = f'aws s3 cp s3://axonius-releases/{version_name}/{version_name}/{version_name}_export.ova' \
                  ' s3://axonius-releases/latest_release/axonius_release.ova' \
                  f' --region {REGION}'

    env = get_env(aws_key, aws_secret)

    log('Copying upgrader to production')
    run_on_subprocess(upgrader_command, env=env, shell=True, check=True, stderr=STDOUT)

    log('Copying OVA to production')
    run_on_subprocess(ova_command, env=env, shell=True, check=True, stderr=STDOUT)

    log('Set latest ami')
    write_file_to_latest_release_bucket(env, ami_id, 'ami_id.txt')

    log('Set latest version')
    write_file_to_latest_release_bucket(env, version_name, 'version_name.txt')

    log('Files copied to production')


def write_file_to_latest_release_bucket(env, data, file_name):
    data_file = Path(file_name)
    data_file.write_text(data)
    set_file_command = f'aws s3 cp {file_name} s3://axonius-releases/latest_release/{file_name}'
    run_on_subprocess(set_file_command, env=env, shell=True, check=True, stderr=STDOUT)
    data_file.unlink()


def create_tag(version_name, commit_hash, **_):
    tag_command = f'git tag {version_name} {commit_hash}'
    push_command = f'git push upstream {version_name}'

    log('Creating tag')
    run_on_subprocess(tag_command, shell=True, check=True, stderr=STDOUT)
    run_on_subprocess(push_command, shell=True, check=True, stderr=STDOUT)


def copy_to_protected_link(aws_key, aws_secret, gen_new_pass, **_):
    should_change_password_arg = '--gen-new-pass' if gen_new_pass else ''
    copy_to_protected_link_command = f'python copy_release_to_protected_link.py --aws-key {aws_key}' \
                                     f' --aws-secret {aws_secret}' \
                                     f' {should_change_password_arg}'
    env = get_env(aws_key, aws_secret)

    log('Copying to protected link')
    run_on_subprocess(copy_to_protected_link_command, env=env, shell=True, check=True, stderr=STDOUT)


def share_with_saas_acount(aws_key, aws_secret, unencrypted_ami_id, **_):
    for dst_region in SAAS_REGIONS:
        ami_share = AmiShare(aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
        image_id_new_region = ami_share.copy_to_region(unencrypted_ami_id, dst_region, is_release=True)
        ami_share.modify_permissions(image_id_new_region, dst_account=AXONIUS_SAAS_ACCOUNT_ID, region=dst_region)
        log(f'Shared AMI with saas account, AMI: {image_id_new_region} region={dst_region}')


def print_epilog(version_name, ami_id, commit_hash, unencrypted_ami_id, **_):

    version_password = VersionPasswords()
    password = version_password.get_password_for_version(version_name)

    base_amazon_url = 'https://axonius-releases.s3-accelerate.amazonaws.com'
    def folder_url(vn): return f'{base_amazon_url}/{vn}/{vn}'
    unencrypted_version_name = version_name + '-unencrypted'

    def vhd(vn): return f'{folder_url(vn)}/{vn}_export.vhdx'
    def qcow(vn): return f'{folder_url(vn)}/{vn}_disk.qcow3'
    def ova(vn): return f'{folder_url(vn)}/{vn}_export.ova'

    log(f'commit_hash: {commit_hash}')
    log(f'ami-id: {ami_id}')
    log(f'unencrypted-ami-id: {unencrypted_ami_id}')
    log(f'decrypt password {password}')
    log(f'OVA link: {ova(version_name)}')
    log(f'VHD link: {vhd(version_name)}')
    log(f'QCOW link: {qcow(version_name)}')
    log(f'Unencrypted OVA link: {ova(unencrypted_version_name)}')
    log(f'Unencrypted VHD link: {vhd(unencrypted_version_name)}')
    log(f'Unencrypted QCOW link: {qcow(unencrypted_version_name)}')
    log(f'Upgrader link: {base_amazon_url}/{version_name}/axonius_{version_name}.py')
    log('Release checklist is finished successfully!')


def main():
    parser = argparse.ArgumentParser(description='Release checklist')

    parser.add_argument('--aws-key', action='store',
                        help='AWS key', required=True)
    parser.add_argument('--aws-secret', action='store',
                        help='AWS secret', required=True)
    parser.add_argument('--version-name', action='store',
                        help='Version name', required=True)
    parser.add_argument('--gen-new-pass', action='store_true', help='Should we generate and set a new password?',
                        required=False, default=False)

    args = parser.parse_args()

    unencrypted_version_name = args.version_name + '-unencrypted'

    builds_instance = Builds()
    export = builds_instance.get_export_by_name(args.version_name)
    export_unencrypted = builds_instance.get_export_by_name(unencrypted_version_name)

    commit_hash = export['git_hash']
    ami_id = export['ami_id']

    arguments = dict(aws_key=args.aws_key,
                     aws_secret=args.aws_secret,
                     version_name=args.version_name,
                     commit_hash=commit_hash,
                     ami_id=ami_id,
                     unencrypted_ami_id=export_unencrypted['ami_id'],
                     gen_new_pass=args.gen_new_pass)

    create_tag(**arguments)

    upload_to_cf_protected_bucket(**arguments)

    upload_to_production(**arguments)

    copy_to_protected_link(**arguments)

    share_with_saas_acount(**arguments)

    print_epilog(**arguments)


if __name__ == '__main__':
    main()
