import argparse

from scripts.automate_dev.latest_ami import get_latest_version
import boto3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version_name', type=str, default='latest')
    parser.add_argument('--customer', type=str, default='')
    parser.add_argument('--expires_in', type=int, default=604800)  # 1 week

    args = parser.parse_args()
    print(args)

    version_name = args.version_name
    expires_in = args.expires_in
    customer = args.customer

    print(f'Creating a pre-signed url of version {version_name} for customer {customer}')

    if version_name == 'latest':
        version_name = get_latest_version()

    try:
        s3_client = boto3.client('s3')
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': 'axonius-releases',
                                                            'Key': f'{version_name}/axonius_{version_name}.py'},
                                                    ExpiresIn=expires_in)
        print(f'Your presigned url is: {response}')

    except Exception as e:
        print(f'Failed to set data {e}')


if __name__ == '__main__':
    main()
