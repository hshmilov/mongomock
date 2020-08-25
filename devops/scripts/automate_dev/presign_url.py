import argparse
import functools
import traceback


from scripts.automate_dev.latest_ami import get_latest_version

from botocore.config import Config
import boto3
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version_name', type=str, default='latest')
    parser.add_argument('--customer', type=str, default='')
    parser.add_argument('--expires_in', type=int, default=604800)  # 1 week
    parser.add_argument('--builds-website-token', type=str, required=False, help='Token to access builds website, '
                                                                                 'needed only if one wants to update '
                                                                                 'builds website with the presigned '
                                                                                 'link')
    parser.add_argument('--notifications-url', type=str, required=False, help='Buildswebsite notifications endpoint')
    parser.add_argument('--disable-notifications-ssl-verify', type=bool, default=False, required=False)

    args = parser.parse_args()
    print(args)

    version_name = args.version_name
    expires_in = args.expires_in
    customer = args.customer

    print(f'Creating a pre-signed url of version {version_name} for customer {customer}')

    if version_name == 'latest':
        version_name = get_latest_version()

    try:
        s3_client = boto3.client('s3', config=Config(s3={'use_accelerate_endpoint': True}))
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': 'axonius-releases',
                                                            'Key': f'{version_name}/axonius_{version_name}.py'},
                                                    ExpiresIn=expires_in)
        print(f'Your presigned url is: {response}')

        print(f'\n\n=======================================')
        print(f'Additional links')
        print(f'=======================================\n\n')
        print(f'Generating more links')
        disk_path = f'{version_name}/{version_name}'

        generate_presigned_bound = functools.partial(generate_presigned_url, s3_client=s3_client,
                                                     notifications_url=args.notifications_url,
                                                     notifications_token=args.builds_website_token,
                                                     expires_in=args.expires_in, version_name=args.version_name,
                                                     disable_ssl_verification=args.disable_notifications_ssl_verify)

        generate_presigned_bound(key=f'{disk_path}/{version_name}_export.ova', ext='ova')
        generate_presigned_bound(key=f'{disk_path}/{version_name}_disk.qcow3', ext='qcow3')
        generate_presigned_bound(key=f'{disk_path}/{version_name}_export.vhdx', ext='vhdx')

    except Exception as e:
        print(f'Failed to set data {e}')


def generate_presigned_url(s3_client, notifications_url, notifications_token, key, ext, expires_in, version_name,
                           disable_ssl_verification):
    response = s3_client.generate_presigned_url('get_object',
                                                Params={'Bucket': 'axonius-releases',
                                                        'Key': key},
                                                ExpiresIn=expires_in)
    print(f'{ext.upper()} link: {response}')
    if notifications_url and notifications_token:
        notify_with_presigned_links(notifications_url=notifications_url, builds_website_token=notifications_token,
                                    version_name=version_name, ext=ext,
                                    new_url=response,
                                    disable_ssl_verification=disable_ssl_verification)
    return response


def notify_with_presigned_links(notifications_url, builds_website_token, version_name, ext, disable_ssl_verification,
                                new_url):
    headers = {'X-Auth-Token': builds_website_token}
    try:
        params = {'name': version_name, 'subcommand': 's3_upload', f's3_{ext}': new_url}
        requests.post(notifications_url, json=params, headers=headers,
                      verify=disable_ssl_verification).raise_for_status()
    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    main()
