import argparse

from scripts.automate_dev.release_checklist import upload_to_cf_protected_bucket


def main():
    parser = argparse.ArgumentParser(description='Release checklist')

    parser.add_argument('--aws-key', action='store',
                        help='AWS key', required=True)
    parser.add_argument('--aws-secret', action='store',
                        help='AWS secret', required=True)
    parser.add_argument('--version-name', action='store',
                        help='Version name', required=True)

    args = parser.parse_args()

    upload_to_cf_protected_bucket(args.aws_key, args.aws_secret, args.version_name)


if __name__ == '__main__':
    main()
